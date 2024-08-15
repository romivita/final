import csv
import os

from comunicacion import Comunicacion
from database_util import query_db
from utils import celda_a_indices


class GestorHojas:

    @staticmethod
    def crear_hoja(mensaje, servidor, conn):
        nombre_hoja = mensaje['nombre']
        usuario_id = mensaje['creador_id']

        hoja_existente = query_db('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?',
                                  (nombre_hoja, usuario_id), one=True)
        if hoja_existente:
            return {"status": "error", "mensaje": "Hoja con ese nombre ya existe"}

        query_db('INSERT INTO hojas_calculo (nombre, creador_id) VALUES (?, ?)', (nombre_hoja, usuario_id))

        hoja_nueva = query_db('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?', (nombre_hoja, usuario_id),
                              one=True)

        hoja_id = hoja_nueva[0]
        archivo_csv = os.path.join(servidor.directorio_archivos, f'{hoja_id}.csv')

        if not os.path.exists(archivo_csv):
            archivo = open(archivo_csv, 'w', newline='')
            try:
                writer = csv.writer(archivo)
                writer.writerow([])
            finally:
                archivo.close()

        GestorHojas.actualizar_mapeo_hojas(conn, hoja_id, servidor)

        return {"status": "ok", "mensaje": "Hoja creada", "hoja_id": hoja_id}

    @staticmethod
    def listar_hojas(usuario_id):
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

        hojas_solo_lectura = query_db('''
            SELECT hc.*, u.usuario 
            FROM hojas_calculo hc
            JOIN permisos p ON hc.id = p.hoja_id
            JOIN usuarios u ON hc.creador_id = u.id
            WHERE p.usuario_id = ? AND p.permisos = 'solo lectura'
        ''', (usuario_id,))

        return {"status": "ok", "hojas_creadas": hojas_creadas, "hojas_lectura_escritura": hojas_lectura_escritura,
                "hojas_solo_lectura": hojas_solo_lectura}

    @staticmethod
    def obtener_hoja_id(mensaje):
        nombre_hoja = mensaje['nombre']
        usuario_id = mensaje['usuario_id']

        hoja = query_db('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?', (nombre_hoja, usuario_id),
                        one=True)

        if not hoja:
            hoja = query_db('''
                SELECT hc.id FROM hojas_calculo hc
                JOIN permisos p ON hc.id = p.hoja_id
                WHERE p.usuario_id = ? AND hc.nombre = ?
            ''', (usuario_id, nombre_hoja), one=True)

        if hoja:
            return {"status": "ok", "hoja_id": hoja[0]}
        else:
            return {"status": "error", "mensaje": "Hoja no encontrada"}

    @staticmethod
    def editar_hoja(mensaje, servidor, conn):
        hoja_id = mensaje['hoja_id']
        celda = mensaje['celda']
        valor = mensaje['valor']
        usuario_id = mensaje['usuario_id']

        servidor.cola_ediciones.put((hoja_id, celda, valor, usuario_id))
        GestorHojas.actualizar_mapeo_hojas(conn, hoja_id, servidor)

        return {"status": "ok", "mensaje": "Edicion en cola"}

    @staticmethod
    def compartir_hoja(mensaje):
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
        return {"status": "ok", "mensaje": "Permisos otorgados"}

    @staticmethod
    def obtener_permisos(mensaje):
        hoja_id = mensaje['hoja_id']
        usuario_id = mensaje['usuario_id']

        creador = query_db('SELECT creador_id FROM hojas_calculo WHERE id=?', (hoja_id,), one=True)
        if creador and creador[0] == usuario_id:
            return {"status": "ok", "permisos": 'lectura y escritura'}
        else:
            permisos = query_db('SELECT permisos FROM permisos WHERE hoja_id=? AND usuario_id=?', (hoja_id, usuario_id),
                                one=True)
            if permisos:
                return {"status": "ok", "permisos": permisos[0]}
            else:
                return {"status": "error", "mensaje": "No se encontraron permisos"}

    @staticmethod
    def leer_datos_csv(hoja_id, servidor, conn):
        archivo_csv = os.path.join(servidor.directorio_archivos, f'{hoja_id}.csv')
        archivo = open(archivo_csv, 'r', newline='')
        try:
            lector = csv.reader(archivo)
            datos = list(lector)
        finally:
            archivo.close()

        if conn not in servidor.hojas_clientes.get(hoja_id, []):
            GestorHojas.actualizar_mapeo_hojas(conn, hoja_id, servidor)

        return {"status": "ok", "datos": datos}

    @staticmethod
    def descargar_hoja(hoja_id):
        archivo_csv = os.path.join(os.path.dirname(__file__), '..', 'hojas_de_calculo', f'{hoja_id}.csv')
        try:
            archivo = open(archivo_csv, 'r', newline='')
            try:
                lector = csv.reader(archivo)
                contenido = list(lector)
                return {"status": "ok", "contenido": contenido}
            except Exception as e:
                return {"status": "error", "mensaje": f"Error al leer el archivo CSV: {e}"}
            finally:
                archivo.close()
        except FileNotFoundError:
            return {"status": "error", "mensaje": "Archivo no encontrado"}

    @staticmethod
    def aplicar_edicion(hoja_id, celda, valor):
        archivo_csv = os.path.join(os.path.dirname(__file__), '..', 'hojas_de_calculo', f'{hoja_id}.csv')
        archivo = open(archivo_csv, 'r', newline='')
        try:
            lector = csv.reader(archivo)
            datos = list(lector)
        finally:
            archivo.close()

        fila, columna = celda_a_indices(celda)

        while len(datos) <= fila:
            datos.append([])

        while len(datos[fila]) <= columna:
            datos[fila].append('')

        datos[fila][columna] = valor

        archivo = open(archivo_csv, 'w', newline='')
        try:
            escritor = csv.writer(archivo)
            escritor.writerows(datos)
        finally:
            archivo.close()

        return {"status": "ok", "mensaje": "Edicion aplicada"}

    @staticmethod
    def notificar_actualizacion(hoja_id, celda, valor, usuario_id, servidor):
        if hoja_id in servidor.hojas_clientes:
            for conn in servidor.hojas_clientes[hoja_id]:
                if conn:
                    Comunicacion.enviar_mensaje(
                        {"accion": "actualizar_celda", "hoja_id": hoja_id, "celda": celda, "valor": valor,
                         "usuario_id": usuario_id}, conn)

    @staticmethod
    def actualizar_mapeo_hojas(conn, hoja_id, servidor):
        if hoja_id not in servidor.hojas_clientes:
            servidor.hojas_clientes[hoja_id] = []

        if conn not in servidor.hojas_clientes[hoja_id]:
            servidor.hojas_clientes[hoja_id].append(conn)
