import hashlib

from database_util import query_db


class Autenticacion:
    @staticmethod
    def iniciar_sesion(mensaje, servidor, conn):
        usuario = mensaje['usuario']
        pwd = mensaje['pwd']
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()

        usuario_data = query_db('SELECT id, pwd_hash FROM usuarios WHERE usuario=?', (usuario,), one=True)

        if usuario_data:
            usuario_id, password_correcta = usuario_data
            if pwd_hash == password_correcta:
                return {"status": "ok", "mensaje": "Sesion iniciada", "usuario_id": usuario_id}
            else:
                return {"status": "error", "mensaje": "Password incorrecto"}
        elif usuario_data is None:
            query_db('INSERT INTO usuarios (usuario, pwd_hash) VALUES (?, ?)', (usuario, pwd_hash))
            usuario_db = query_db('SELECT * FROM usuarios WHERE usuario=?', (usuario,), one=True)
            return {"status": "ok", "mensaje": "Cuenta creada", "usuario_id": usuario_db[0]}
