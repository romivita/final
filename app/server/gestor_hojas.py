import csv
import os

from database_util import Database


class GestorDeHojas:
    def __init__(self, servidor):
        self.servidor = servidor
        self.directorio_archivos = servidor.directorio_archivos

    def crear_hoja(self, mensaje):
        nombre_hoja = mensaje.get("nombre")
        usuario_id = mensaje.get("usuario_id")

        with Database() as db:
            hoja_existe = db.query('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?',
                                   (nombre_hoja, usuario_id), one=True)
            if hoja_existe:
                return {"status": "error", "mensaje": "Ya existe una hoja con ese nombre"}

            cursor = db.execute('INSERT INTO hojas_calculo (nombre, creador_id) VALUES (?, ?)',
                                (nombre_hoja, usuario_id))
            hoja_id = cursor.lastrowid

            db.execute('INSERT INTO permisos (hoja_id, usuario_id, permisos) VALUES (?, ?, ?)',
                       (hoja_id, usuario_id, 'propietario'))

        self.crear_archivo_csv(hoja_id)

        return {"status": "ok", "mensaje": "Hoja creada", "hoja_id": hoja_id}

    def crear_archivo_csv(self, hoja_id):
        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')
        if not os.path.exists(archivo_csv):
            with open(archivo_csv, 'w', newline='') as archivo:
                csv.writer(archivo).writerow([])

    def listar_hojas(self, mensaje, conn):
        self.servidor.eliminar_conexion(conn)
        usuario_id = mensaje.get("usuario_id")
        hojas = {"hojas_creadas": self.obtener_hojas_con_permisos(usuario_id, 'propietario'),
                 "hojas_lectura_escritura": self.obtener_hojas_con_permisos(usuario_id, 'lectura y escritura'),
                 "hojas_solo_lectura": self.obtener_hojas_con_permisos(usuario_id, 'solo lectura')}
        return {"status": "ok", **hojas}

    @staticmethod
    def obtener_hojas_con_permisos(usuario_id, permiso):
        with Database() as db:
            hojas = db.query('''
                SELECT h.*, u.usuario 
                FROM hojas_calculo h
                JOIN permisos p ON h.id = p.hoja_id
                JOIN usuarios u ON h.creador_id = u.id
                WHERE p.usuario_id = ? AND p.permisos = ?
            ''', (usuario_id, permiso))

        return hojas

    @staticmethod
    def obtener_hoja_id(mensaje):
        nombre_hoja = mensaje.get("nombre")
        usuario_id = mensaje.get("usuario_id")

        with Database() as db:
            hoja = db.query('SELECT id FROM hojas_calculo WHERE nombre=? AND creador_id=?', (nombre_hoja, usuario_id),
                            one=True)

            if not hoja:
                hoja = db.query('''
                    SELECT hc.id FROM hojas_calculo hc
                    JOIN permisos p ON hc.id = p.hoja_id
                    WHERE p.usuario_id = ? AND hc.nombre = ?
                ''', (usuario_id, nombre_hoja), one=True)

        if hoja:
            return {"status": "ok", "hoja_id": hoja[0]}
        else:
            return {"status": "error", "mensaje": "No se encontro la hoja"}

    def editar_celda(self, mensaje, conn):
        hoja_id = mensaje.get("hoja_id")
        self.servidor.cola_ediciones.agregar_edicion(mensaje)
        self.servidor.asociar_cliente_hoja(conn, hoja_id)
        return {"status": "ok", "mensaje": "Edicion registrada"}

    def compartir_hoja(self, mensaje):
        hoja_id = mensaje.get("hoja_id")
        nombre_usuario = mensaje.get("nombre_usuario")
        permisos = mensaje.get("permisos")

        with Database() as db:
            usuario = db.query('SELECT id FROM usuarios WHERE usuario=?', (nombre_usuario,), one=True)
            if not usuario:
                return {"status": "error", "mensaje": "Usuario no encontrado"}

            usuario_id = usuario[0]

            hoja = db.query('SELECT creador_id FROM hojas_calculo WHERE id=?', (hoja_id,), one=True)
            if not hoja:
                return {"status": "error", "mensaje": "Hoja no encontrada"}

            if hoja[0] == usuario_id:
                return {"status": "error", "mensaje": "No puedes compartir la hoja contigo mismo"}

            db.execute('INSERT OR REPLACE INTO permisos (hoja_id, usuario_id, permisos) VALUES (?, ?, ?)',
                       (hoja_id, usuario_id, permisos))

        return {"status": "ok", "mensaje": "Permisos otorgados"}

    def obtener_permisos_usuario(self, mensaje):
        hoja_id = mensaje.get("hoja_id")
        usuario_id = mensaje.get("usuario_id")

        with Database() as db:
            permisos = db.query('SELECT permisos FROM permisos WHERE hoja_id=? AND usuario_id=?', (hoja_id, usuario_id),
                                one=True)

        if permisos:
            return {"status": "ok", "permisos": permisos[0]}
        else:
            return None

    def leer_datos_csv(self, mensaje, conn):
        hoja_id = mensaje.get("hoja_id")
        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')

        if os.path.exists(archivo_csv):
            with open(archivo_csv, 'r', newline='') as archivo:
                datos = list(csv.reader(archivo))
            self.servidor.asociar_cliente_hoja(conn, hoja_id)
            return {"status": "ok", "datos": datos}
        else:
            return {"status": "error", "mensaje": "Archivo no encontrado"}

    def descargar_hoja(self, mensaje):
        hoja_id = mensaje.get("hoja_id")
        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')

        if os.path.exists(archivo_csv):
            with open(archivo_csv, 'r') as archivo:
                contenido_csv = archivo.read()
            return {"status": "ok", "contenido_csv": contenido_csv}
        else:
            return {"status": "error", "mensaje": "No se encontro el archivo"}

    def eliminar_hoja(self, mensaje):
        hoja_id = mensaje.get("hoja_id")

        with Database() as db:
            db.execute('DELETE FROM hojas_calculo WHERE id=?', (hoja_id,))
            db.execute('DELETE FROM permisos WHERE hoja_id=?', (hoja_id,))

        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')
        if os.path.exists(archivo_csv):
            os.remove(archivo_csv)

        return {"status": "ok", "mensaje": "Hoja eliminada"}
