import hashlib

from database_util import Database


class Autenticacion:
    def __init__(self, servidor):
        self.servidor = servidor

    def iniciar_sesion(self, mensaje, conn):
        usuario = mensaje.get("usuario")
        pwd_hash = hashlib.sha256(mensaje.get("pwd").encode()).hexdigest()

        with Database() as db:
            usuario_data = db.query('SELECT id, pwd_hash FROM usuarios WHERE usuario=?', (usuario,), one=True)

            if usuario_data:
                usuario_id, pwd_correcta = usuario_data
                if pwd_hash == pwd_correcta:
                    self.servidor.asociar_cliente_hojas(conn, [])
                    return {"status": "ok", "mensaje": "Sesion iniciada", "usuario_id": usuario_id}
                else:
                    return {"status": "error", "mensaje": "Contraseña incorrecta"}

            cursor = db.execute('INSERT INTO usuarios (usuario, pwd_hash) VALUES (?, ?)', (usuario, pwd_hash))
            usuario_id = cursor.lastrowid

        return {"status": "ok", "mensaje": "Cuenta creada", "usuario_id": usuario_id}
