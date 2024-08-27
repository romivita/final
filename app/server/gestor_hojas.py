import csv
import os

from database_util import query_db


class GestorDeHojas:
    def __init__(self, servidor):
        self.servidor = servidor
        self.directorio_archivos = servidor.directorio_archivos

    def crear_hoja(self, mensaje, conn):
        nombre_hoja = mensaje['nombre']
        usuario_id = mensaje['usuario_id']

        hoja_existente = query_db('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?',
                                  (nombre_hoja, usuario_id), one=True)
        if hoja_existente:
            return {"status": "error", "mensaje": "Ya existe una hoja con ese nombre"}

        query_db('INSERT INTO hojas_calculo (nombre, creador_id) VALUES (?, ?)', (nombre_hoja, usuario_id))
        hoja_id = \
        query_db('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?', (nombre_hoja, usuario_id), one=True)[0]
        query_db('INSERT INTO permisos (hoja_id, usuario_id, permisos) VALUES (?, ?, ?)',
                 (hoja_id, usuario_id, 'propietario'))

        self.crear_archivo_csv(hoja_id)
        self.servidor.asociar_cliente_hoja(conn, hoja_id)

        return {"status": "ok", "mensaje": "Hoja creada", "hoja_id": hoja_id}

    def crear_archivo_csv(self, hoja_id):
        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')
        if not os.path.exists(archivo_csv):
            with open(archivo_csv, 'w', newline='') as archivo:
                csv.writer(archivo).writerow([])

    def listar_hojas(self, mensaje):
        usuario_id = mensaje['usuario_id']
        hojas_creadas = self.obtener_hojas_con_permisos(usuario_id, 'propietario')
        hojas_lectura_escritura = self.obtener_hojas_con_permisos(usuario_id, 'lectura y escritura')
        hojas_solo_lectura = self.obtener_hojas_con_permisos(usuario_id, 'solo lectura')

        return {"status": "ok", "hojas_creadas": hojas_creadas, "hojas_lectura_escritura": hojas_lectura_escritura,
                "hojas_solo_lectura": hojas_solo_lectura}

    def obtener_hojas_con_permisos(self, usuario_id, permiso):
        return query_db('''
            SELECT h.*, u.usuario 
            FROM hojas_calculo h
            JOIN permisos p ON h.id = p.hoja_id
            JOIN usuarios u ON h.creador_id = u.id
            WHERE p.usuario_id = ? AND p.permisos = ?
        ''', (usuario_id, permiso))

    def obtener_hoja_id(self, mensaje):
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
            return {"status": "error", "mensaje": "No se encontró la hoja"}

    def editar_celda(self, mensaje, conn):
        hoja_id = mensaje['hoja_id']

        self.servidor.cola_ediciones.agregar_edicion(mensaje)
        self.servidor.asociar_cliente_hoja(conn, hoja_id)
        return {"status": "ok", "mensaje": "Edición registrada"}

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
        return {"status": "ok", "mensaje": "Permisos otorgados"}

    def obtener_permisos_usuario(self, mensaje):
        hoja_id = mensaje['hoja_id']
        usuario_id = mensaje['usuario_id']

        permisos = query_db('SELECT permisos FROM permisos WHERE hoja_id=? AND usuario_id=?', (hoja_id, usuario_id),
                            one=True)
        if permisos:
            return {"status": "ok", "permisos": permisos[0]}
        else:
            None

    def leer_datos_csv(self, mensaje, conn):
        hoja_id = mensaje['hoja_id']

        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')
        with open(archivo_csv, 'r', newline='') as archivo:
            datos = list(csv.reader(archivo))
        self.servidor.asociar_cliente_hoja(conn, hoja_id)
        return {"status": "ok", "datos": datos}

    def descargar_hoja(self, mensaje):
        hoja_id = mensaje['hoja_id']
        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')

        if os.path.exists(archivo_csv):
            with open(archivo_csv, 'r') as archivo:
                contenido_csv = archivo.read()
            return {"status": "ok", "contenido_csv": contenido_csv}
        else:
            return {"status": "error", "mensaje": "No se encontró el archivo"}

    def eliminar_hoja(self, mensaje):
        hoja_id = mensaje['hoja_id']

        query_db('DELETE FROM hojas_calculo WHERE id=?', (hoja_id,))
        query_db('DELETE FROM permisos WHERE hoja_id=?', (hoja_id,))

        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')
        if os.path.exists(archivo_csv):
            os.remove(archivo_csv)

        return {"status": "ok", "mensaje": "Hoja eliminada"}
