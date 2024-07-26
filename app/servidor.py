import csv
import json
import os
import signal
import socket
import time
from queue import Queue
from threading import Thread, Lock

from config_util import cargar_configuracion
from database_util import (inicializar_bd, verificar_credenciales, obtener_hojas_usuario, crear_hoja_bd, hoja_existe_bd,
                           compartir_hoja_bd, usuario_existe, crear_usuario)
from utils import celda_a_indices, safe_eval


class Servidor:
    def __init__(self):
        self.host, self.port = cargar_configuracion()
        self.clientes = []
        self.hojas_de_calculo_dict = {}
        self.usuarios_hojas_compartidas = {}
        self.cola = Queue(maxsize=100)
        self.lock = Lock()
        self.socket_servidor = self.inicializar_socket()
        self.crear_directorio_hojas_de_calculo()
        self.escritor_thread = Thread(target=self.procesar_cola)
        self.escritor_thread.start()
        inicializar_bd()
        signal.signal(signal.SIGINT, self.manejar_sigint)

    def inicializar_socket(self):
        try:
            socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            socket_servidor.bind((self.host, self.port))
            return socket_servidor
        except Exception as e:
            print(f"Error al inicializar el socket: {e}")
            raise

    def crear_directorio_hojas_de_calculo(self):
        ruta_directorio = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hojas_de_calculo'))
        if not os.path.exists(ruta_directorio):
            os.makedirs(ruta_directorio)
            print(f"Directorio {ruta_directorio} creado.")

    def procesar_cola(self):
        while True:
            try:
                hoja_id, celda, valor = self.cola.get()
                if valor.startswith('='):
                    try:
                        valor = str(safe_eval(valor[1:]))
                    except Exception as e:
                        valor = f"Error: {e}"
                fila, columna = celda_a_indices(celda)
                self.hojas_de_calculo_dict.setdefault(hoja_id, {})[(fila, columna)] = valor
                self.guardar_en_csv(hoja_id)
                self.notificar_clientes(hoja_id, celda, valor)
                self.cola.task_done()
            except Exception as e:
                print(f"Error procesando la cola: {e}")
            time.sleep(0.1)

    def gestionar_cliente(self, cliente_socket, cliente_address):
        print(f"Conexión establecida con {cliente_address}")
        self.clientes.append((cliente_socket, cliente_address))
        try:
            self.loop_cliente(cliente_socket)
        finally:
            cliente_socket.close()
            self.clientes.remove((cliente_socket, cliente_address))
            for user in self.usuarios_hojas_compartidas.values():
                if cliente_socket in user:
                    user.remove(cliente_socket)
            print(f"Conexión cerrada con {cliente_address}")

    def loop_cliente(self, cliente_socket):
        try:
            data = cliente_socket.recv(4096).decode()
            print(f"Datos recibidos: {data}")
            if not data:
                return

            mensaje = json.loads(data)
            usuario = mensaje.get("usuario")
            if not usuario:
                self.enviar_error(cliente_socket, "Usuario no proporcionado")
                return

            usuario_id = usuario_existe(usuario)
            if usuario_id:
                cliente_socket.sendall(json.dumps({"status": "existe"}).encode())
                data = cliente_socket.recv(4096).decode()
                if not data:
                    return
                mensaje = json.loads(data)
                pwd = mensaje.get("pwd")
                if not pwd:
                    self.enviar_error(cliente_socket, "Contraseña no proporcionada")
                    return

                usuario_id = verificar_credenciales(usuario, pwd)
                if not usuario_id:
                    self.enviar_error(cliente_socket, "Credenciales inválidas")
                    return

                hojas_usuario = obtener_hojas_usuario(usuario_id)
                cliente_socket.sendall(json.dumps({"status": "OK", "hojas": hojas_usuario}).encode())
            else:
                cliente_socket.sendall(json.dumps({"status": "no_existe"}).encode())
                data = cliente_socket.recv(4096).decode()
                if not data:
                    return
                mensaje = json.loads(data)
                if mensaje.get("crear_nuevo_usuario"):
                    pwd_hash = mensaje.get("pwd")
                    if pwd_hash:
                        try:
                            usuario_id = crear_usuario(usuario, pwd_hash)
                            if usuario_id:
                                cliente_socket.sendall(json.dumps({"status": "nuevo_usuario_creado"}).encode())
                                hojas_usuario = obtener_hojas_usuario(usuario_id)
                                cliente_socket.sendall(json.dumps({"status": "OK", "hojas": hojas_usuario}).encode())
                            else:
                                self.enviar_error(cliente_socket, "Error al crear el usuario")
                        except Exception as e:
                            self.enviar_error(cliente_socket, f"Error al crear el usuario: {e}")
                    else:
                        self.enviar_error(cliente_socket, "Contraseña no proporcionada para el nuevo usuario")
                else:
                    self.enviar_error(cliente_socket, "Solicitud de creación de usuario no válida")
                return

            while True:
                data = cliente_socket.recv(4096).decode()
                if not data:
                    break

                try:
                    mensaje = json.loads(data)
                    print(f"Mensaje recibido: {mensaje}")  # Mensaje de depuración
                    opcion = mensaje.get("opcion", None)
                    hoja_id = mensaje.get("hoja_id", None)

                    if opcion:
                        if opcion == "nueva":
                            hoja_id = self.inicializar_hoja(mensaje.get("nombre_hoja"), usuario_id)
                            self.importar_csv_a_dict(hoja_id)
                            print(
                                f"Enviando respuesta al cliente: {json.dumps({'status': 'OK', 'hoja_id': f'{hoja_id}'})}")
                            cliente_socket.sendall(json.dumps({"status": "OK", "hoja_id": f"{hoja_id}"}).encode())

                            # Ahora enviar la hoja completa
                            self.enviar_hoja_completa(cliente_socket, hoja_id)
                            self.asignar_permisos_cliente_dict(cliente_socket, hoja_id)
                        elif opcion == "existente":
                            if hoja_existe_bd(hoja_id, usuario_id):
                                self.importar_csv_a_dict(hoja_id)
                                self.enviar_hoja_completa(cliente_socket, hoja_id)
                                self.asignar_permisos_cliente_dict(cliente_socket, hoja_id)
                            else:
                                self.enviar_error(cliente_socket, "La hoja de calculo no existe")
                        elif opcion == "compartir":
                            usuario_compartido = mensaje.get("usuario_compartido", None)
                            if usuario_compartido:
                                self.compartir_hoja(hoja_id, usuario_compartido, usuario_id, cliente_socket)
                            else:
                                self.enviar_error(cliente_socket, "Falta el usuario con quien compartir")
                        elif opcion == "descargar":
                            self.enviar_csv(cliente_socket, hoja_id)
                        elif opcion == "registrar":
                            self.asignar_permisos_cliente_dict(cliente_socket, hoja_id)
                        else:
                            self.enviar_error(cliente_socket, "Opción no válida")
                    else:
                        if 'hoja_id' in mensaje and 'celda' in mensaje and 'valor' in mensaje:
                            hoja_id = mensaje.get("hoja_id")
                            celda = mensaje.get("celda")
                            valor = mensaje.get("valor", "")
                            fila, columna = celda_a_indices(celda)
                            valor = f"{valor}({usuario})"
                            self.cola.put((hoja_id, celda, valor))
                            self.hojas_de_calculo_dict[hoja_id][fila][columna] = valor
                            cliente_socket.sendall(json.dumps({"status": "OK"}).encode())
                        else:
                            self.enviar_error(cliente_socket, "Mensaje no válido")

                except json.JSONDecodeError as e:
                    self.enviar_error(cliente_socket, f"Error al decodificar el JSON: {e}")
        except Exception as e:
            print(f"Error en la comunicación con el cliente: {e}")
        finally:
            cliente_socket.close()

    def enviar_csv(self, cliente_socket, hoja_id):
        ruta_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{hoja_id}.csv"))
        try:
            archivo = open(ruta_csv, "r")
            try:
                contenido = archivo.read()
                mensaje = json.dumps({"csv": contenido})
                cliente_socket.sendall(mensaje.encode())
            finally:
                archivo.close()
        except FileNotFoundError:
            self.enviar_error(cliente_socket, f"El archivo {hoja_id}.csv no existe.")
        except Exception as e:
            self.enviar_error(cliente_socket, f"Error al enviar el archivo {hoja_id}.csv: {e}")

    def enviar_error(self, cliente_socket, mensaje):
        error_msg = json.dumps({"status": "error", "mensaje": mensaje})
        cliente_socket.sendall(error_msg.encode())

    def inicializar_hoja(self, nombre_hoja, usuario_id):
        hoja_id = crear_hoja_bd(nombre_hoja, usuario_id)
        self.hojas_de_calculo_dict[hoja_id] = {}
        self.guardar_en_csv(hoja_id)
        return hoja_id

    def importar_csv_a_dict(self, hoja_id):
        ruta_hoja = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{hoja_id}.csv"))
        if not os.path.exists(ruta_hoja):
            return
        with open(ruta_hoja, 'r', newline='') as archivo:
            reader = csv.reader(archivo)
            for fila_idx, fila in enumerate(reader):
                for col_idx, valor in enumerate(fila):
                    if valor:
                        self.hojas_de_calculo_dict.setdefault(hoja_id, {})[(fila_idx, col_idx)] = valor

    def guardar_en_csv(self, hoja_id):
        filas_max = max(fila for fila, _ in self.hojas_de_calculo_dict[hoja_id]) if self.hojas_de_calculo_dict[
            hoja_id] else 0
        columnas_max = max(columna for _, columna in self.hojas_de_calculo_dict[hoja_id]) if self.hojas_de_calculo_dict[
            hoja_id] else 0

        ruta_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{hoja_id}.csv"))
        file = open(ruta_csv, "w", newline='')
        try:
            writer = csv.writer(file)
            for fila in range(1, filas_max + 1):
                fila_datos = [self.hojas_de_calculo_dict[hoja_id].get((fila, columna), "") for columna in
                              range(1, columnas_max + 1)]
                writer.writerow(fila_datos)
        finally:
            file.close()

    def enviar_hoja_completa(self, cliente_socket, hoja_id):
        self.lock.acquire()
        try:
            hoja = self.hojas_de_calculo_dict.get(hoja_id, {})
        finally:
            self.lock.release()

        # Transformar los datos de la hoja en un formato que pueda ser decodificado correctamente en JSON
        datos_hoja = [[hoja.get((fila, col), '') for col in range(10)] for fila in range(10)]
        mensaje = {"hoja_id": f"{hoja_id}", "datos": datos_hoja}
        cliente_socket.sendall((json.dumps(mensaje) + "\n").encode())

    def asignar_permisos_cliente_dict(self, cliente_socket, hoja_id):
        if hoja_id not in self.usuarios_hojas_compartidas:
            self.usuarios_hojas_compartidas[hoja_id] = []
        self.usuarios_hojas_compartidas[hoja_id].append(cliente_socket)

    def notificar_clientes(self, hoja_id, celda, valor):
        if hoja_id in self.usuarios_hojas_compartidas:
            for cliente in self.usuarios_hojas_compartidas[hoja_id]:
                mensaje = json.dumps({"hoja_id": f"{hoja_id}", "celda": celda, "valor": valor})
                cliente.sendall(mensaje.encode())

    def compartir_hoja(self, hoja_id, usuario_compartido, usuario_id, cliente_socket):
        resultado = compartir_hoja_bd(hoja_id, usuario_compartido, usuario_id)
        if "error" in resultado:
            self.enviar_error(cliente_socket, resultado["error"])
        else:
            cliente_socket.sendall(json.dumps({"status": "OK"}).encode())

    def iniciar_servidor(self):
        self.socket_servidor.listen(5)
        print("Servidor escuchando en", (self.host, self.port))
        while True:
            cliente_socket, cliente_address = self.socket_servidor.accept()
            cliente_thread = Thread(target=self.gestionar_cliente, args=(cliente_socket, cliente_address))
            cliente_thread.start()

    def manejar_sigint(self, signum, frame):
        print("\nTerminando el servidor...")
        self.socket_servidor.close()
        os._exit(0)


if __name__ == "__main__":
    servidor = Servidor()
    servidor.iniciar_servidor()
