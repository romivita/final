import csv
import hashlib
import os
import queue
import signal
import socket
import sys
import threading

from comunicacion import Comunicacion
from config_util import cargar_configuracion
from database_util import query_db
from utils import celda_a_indices


class Servidor:
    def __init__(self):
        self.host, self.port = cargar_configuracion()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.hilos = []
        self.clientes_conectados = {}
        self.hojas_clientes = {}
        self.cola_ediciones = queue.Queue()
        self.lock = threading.Lock()
        print(f"Servidor iniciado en {self.host}:{self.port}")

        self.directorio_archivos = 'hojas_de_calculo'
        if not os.path.exists(self.directorio_archivos):
            os.makedirs(self.directorio_archivos)

        signal.signal(signal.SIGINT, self.terminar_servidor)

        hilo_procesar_cola = threading.Thread(target=self.procesar_cola_ediciones, daemon=True)
        hilo_procesar_cola.start()

    def procesar_mensaje(self, mensaje, conn):
        if mensaje['accion'] == 'iniciar_sesion':
            respuesta = self.iniciar_sesion(mensaje)
            if respuesta.get('status') == 'ok':
                self.lock.acquire()
                try:
                    self.clientes_conectados[conn] = respuesta['usuario_id']
                finally:
                    self.lock.release()
            return respuesta
        elif mensaje['accion'] == 'crear_hoja':
            respuesta = self.crear_hoja(mensaje)
            if respuesta.get('status') == 'ok':
                self.actualizar_mapeo_hojas(mensaje['creador_id'], conn, respuesta['hoja_id'])
            return respuesta
        elif mensaje['accion'] == 'listar_hojas':
            return self.listar_hojas(mensaje)
        elif mensaje['accion'] == 'obtener_hoja_id':
            return self.obtener_hoja_id(mensaje)
        elif mensaje['accion'] == 'editar_hoja':
            hoja_id = mensaje['hoja_id']
            celda = mensaje['celda']
            valor = mensaje['valor']
            usuario_id = mensaje['usuario_id']
            self.cola_ediciones.put((hoja_id, celda, valor, usuario_id))
            self.actualizar_mapeo_hojas(usuario_id, conn, hoja_id)
            return {"status": "ok"}
        elif mensaje['accion'] == 'compartir_hoja':
            return self.compartir_hoja(mensaje)
        elif mensaje['accion'] == 'ver_hoja':
            respuesta = self.ver_hoja(mensaje, conn)
            if respuesta.get('status') == 'ok':
                self.actualizar_mapeo_hojas(mensaje['usuario_id'], conn, mensaje['hoja_id'])
            return respuesta
        elif mensaje['accion'] == 'desconectar':
            return {"status": "ok", "mensaje": "Desconectado"}
        return {"status": "error", "mensaje": "Acción no válida"}

    def iniciar_sesion(self, mensaje):
        usuario = mensaje['usuario']
        pwd = mensaje['pwd']
        usuario_db = query_db('SELECT * FROM usuarios WHERE usuario=?', (usuario,), one=True)
        if usuario_db:
            pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
            if usuario_db[2] == pwd_hash:
                return {"status": "ok", "mensaje": "Inicio de sesión exitoso", "usuario_id": usuario_db[0]}
            else:
                return {"status": "error", "mensaje": "Contraseña incorrecta"}
        else:
            pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
            query_db('INSERT INTO usuarios (usuario, pwd_hash) VALUES (?, ?)', (usuario, pwd_hash))
            usuario_db = query_db('SELECT * FROM usuarios WHERE usuario=?', (usuario,), one=True)
            return {"status": "ok", "mensaje": "Cuenta creada", "usuario_id": usuario_db[0]}

    def crear_hoja(self, mensaje):
        hoja_existente = query_db('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?',
                                  (mensaje['nombre'], mensaje['creador_id']), one=True)
        if hoja_existente:
            return {"status": "error", "mensaje": "Hoja con ese nombre ya existe"}

        query_db('INSERT INTO hojas_calculo (nombre, creador_id) VALUES (?, ?)',
                 (mensaje['nombre'], mensaje['creador_id']))

        hoja_nueva = query_db('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?',
                              (mensaje['nombre'], mensaje['creador_id']), one=True)

        hoja_id = hoja_nueva[0]
        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')
        if not os.path.exists(archivo_csv):
            archivo = open(archivo_csv, 'w', newline='')
            try:
                writer = csv.writer(archivo)
                writer.writerow([])
            finally:
                archivo.close()

        return {"status": "ok", "mensaje": "Hoja creada", "hoja_id": hoja_id}

    def listar_hojas(self, mensaje):
        usuario_id = mensaje['creador_id']

        hojas_creadas = query_db('''
            SELECT hc.*, u.usuario 
            FROM hojas_calculo hc 
            JOIN usuarios u ON hc.creador_id = u.id 
            WHERE hc.creador_id = ?
        ''', (usuario_id,))

        hojas_lectura_escritura = query_db('''
            SELECT hc.*, u.usuario 
            FROM hojas_calculo hc
            JOIN permisos p ON hc.id = p.hoja_id
            JOIN usuarios u ON hc.creador_id = u.id
            WHERE p.usuario_id = ? AND p.permisos = 'lectura y escritura'
        ''', (usuario_id,))

        hojas_lectura = query_db('''
            SELECT hc.*, u.usuario 
            FROM hojas_calculo hc
            JOIN permisos p ON hc.id = p.hoja_id
            JOIN usuarios u ON hc.creador_id = u.id
            WHERE p.usuario_id = ? AND p.permisos = 'solo lectura'
        ''', (usuario_id,))

        return {"status": "ok", "hojas_creadas": hojas_creadas, "hojas_lectura_escritura": hojas_lectura_escritura,
                "hojas_lectura": hojas_lectura}

    def obtener_hoja_id(self, mensaje):
        nombre_hoja = mensaje['nombre']
        usuario_id = mensaje['usuario_id']

        hoja = query_db('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?', (nombre_hoja, usuario_id),
                        one=True)

        if not hoja:
            hoja = query_db('''
                SELECT hc.id FROM hojas_calculo hc
                JOIN permisos p ON hc.id = p.hoja_id
                WHERE hc.nombre=? AND p.usuario_id=?
            ''', (nombre_hoja, usuario_id), one=True)

        if hoja:
            return {"status": "ok", "hoja_id": hoja[0]}
        else:
            return {"status": "error", "mensaje": "Hoja no encontrada"}

    def compartir_hoja(self, mensaje):
        hoja_id = mensaje['hoja_id']
        nombre_usuario = mensaje['nombre_usuario']
        permisos = mensaje['permisos']

        usuario = query_db('SELECT id FROM usuarios WHERE usuario=?', (nombre_usuario,), one=True)
        if not usuario:
            return {"status": "error", "mensaje": "Usuario no encontrado"}

        usuario_id = usuario[0]

        hoja = query_db('SELECT creador_id FROM hojas_calculo WHERE id=?', (hoja_id,), one=True)
        if not hoja:
            return {"status": "error", "mensaje": "Hoja no encontrada"}

        creador_id = hoja[0]
        if creador_id == usuario_id:
            return {"status": "error", "mensaje": "No puedes compartir la hoja contigo mismo"}

        query_db('INSERT OR REPLACE INTO permisos (hoja_id, usuario_id, permisos) VALUES (?, ?, ?)',
                 (hoja_id, usuario_id, permisos))
        return {"status": "ok", "mensaje": "Hoja compartida exitosamente"}

    def ver_hoja(self, mensaje, conn):
        hoja_id = mensaje['hoja_id']
        usuario_id = mensaje['usuario_id']

        creador = query_db('SELECT creador_id FROM hojas_calculo WHERE id=?', (hoja_id,), one=True)
        if creador and creador[0] == usuario_id:
            permisos_usuario = 'lectura y escritura'
        else:
            permisos = query_db('SELECT permisos FROM permisos WHERE hoja_id=? AND usuario_id=?', (hoja_id, usuario_id),
                                one=True)
            permisos_usuario = permisos[0] if permisos else None

        if not permisos_usuario:
            return {"status": "error", "mensaje": "No tienes permisos para ver esta hoja"}

        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')

        if not os.path.exists(archivo_csv):
            return {"status": "error", "mensaje": "Archivo de hoja de cálculo no encontrado"}

        datos = []

        archivo = open(archivo_csv, 'r', newline='')
        try:
            lector = csv.reader(archivo)
            datos = list(lector)
        except Exception as e:
            print(f"Error al leer el archivo CSV: {e}")
        finally:
            archivo.close()

        return {"status": "ok", "datos": datos, "permisos": permisos_usuario}

    def actualizar_mapeo_hojas(self, usuario_id, conn, hoja_id):
        self.lock.acquire()
        try:
            if hoja_id not in self.hojas_clientes:
                self.hojas_clientes[hoja_id] = set()
            if conn not in self.hojas_clientes[hoja_id]:
                self.hojas_clientes[hoja_id].add(conn)
        finally:
            self.lock.release()

    def aplicar_edicion(self, hoja_id, celda, valor):
        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')

        if not os.path.exists(archivo_csv):
            return {"status": "error", "mensaje": "Archivo de hoja de cálculo no encontrado"}

        try:
            archivo = open(archivo_csv, 'r', newline='')
            try:
                lector = csv.reader(archivo)
                datos = list(lector)
                indices = celda_a_indices(celda)

                if indices[0] >= len(datos):
                    datos.extend([[] for _ in range(indices[0] - len(datos) + 1)])
                if indices[1] >= len(datos[indices[0]]):
                    datos[indices[0]].extend([''] * (indices[1] - len(datos[indices[0]]) + 1))
                datos[indices[0]][indices[1]] = valor
            except Exception as e:
                print(f"Error al leer el archivo CSV: {e}")
            finally:
                archivo.close()

            archivo = open(archivo_csv, 'w', newline='')
            try:
                escritor = csv.writer(archivo)
                escritor.writerows(datos)
            except Exception as e:
                print(f"Error al escribir en el archivo CSV: {e}")
            finally:
                archivo.close()

            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "mensaje": f"Error al aplicar edición: {e}"}

    def notificar_actualizacion(self, hoja_id, celda, valor, usuario_id):
        mensaje_actualizacion = {"accion": "actualizacion", "hoja_id": hoja_id, "celda": celda, "valor": valor,
                                 "usuario_id": usuario_id}
        if hoja_id in self.hojas_clientes:
            for conn in self.hojas_clientes[hoja_id]:
                try:
                    Comunicacion.enviar(mensaje_actualizacion, conn)
                except Exception as e:
                    print(f"Error al enviar notificación a {conn}: {e}")

    def procesar_cola_ediciones(self):
        while True:
            hoja_id, celda, valor, usuario_id = self.cola_ediciones.get()
            resultado = self.aplicar_edicion(hoja_id, celda, valor)
            if resultado["status"] == "ok":
                self.notificar_actualizacion(hoja_id, celda, valor, usuario_id)
            self.cola_ediciones.task_done()

    def manejar_cliente(self, conn, addr):
        print(f"Conexión desde {addr}")
        self.lock.acquire()
        try:
            self.clientes_conectados[conn] = addr
        finally:
            self.lock.release()

        try:
            while True:
                mensaje = Comunicacion.recibir(conn)
                if not mensaje:
                    break
                print(conn)
                respuesta = self.procesar_mensaje(mensaje, conn)
                Comunicacion.enviar(respuesta, conn)

                if mensaje['accion'] == 'desconectar':
                    break
        finally:
            conn.close()
            self.lock.acquire()
            try:
                del self.clientes_conectados[conn]
                for hoja_id in list(self.hojas_clientes.keys()):
                    if conn in self.hojas_clientes[hoja_id]:
                        self.hojas_clientes[hoja_id].remove(conn)
                        if not self.hojas_clientes[hoja_id]:
                            del self.hojas_clientes[hoja_id]
            finally:
                self.lock.release()

    def iniciar(self):
        print("Servidor iniciado, esperando conexiones...")
        while True:
            conn, addr = self.sock.accept()
            hilo_cliente = threading.Thread(target=self.manejar_cliente, args=(conn, addr))
            hilo_cliente.start()
            self.hilos.append(hilo_cliente)

    def terminar_servidor(self, sig, frame):
        print("Terminando servidor...")
        self.sock.close()
        for hilo in self.hilos:
            hilo.join()
        sys.exit(0)


if __name__ == '__main__':
    servidor = Servidor()
    servidor.iniciar()
