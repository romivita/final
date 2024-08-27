import hashlib

from database_util import query_db


class Autenticacion:
    def __init__(self, servidor):
        self.servidor = servidor

    def iniciar_sesion(self, mensaje, conn):
        usuario = mensaje['usuario']
        pwd_hash = hashlib.sha256(mensaje['pwd'].encode()).hexdigest()

        usuario_data = query_db('SELECT id, pwd_hash FROM usuarios WHERE usuario=?', (usuario,), one=True)

        if usuario_data:
            usuario_id, pwd_correcta = usuario_data
            if pwd_hash == pwd_correcta:
                self.servidor.asociar_cliente_hojas(conn, [])
                return {"status": "ok", "mensaje": "Sesión iniciada", "usuario_id": usuario_id}
            return {"status": "error", "mensaje": "Contraseña incorrecta"}

        query_db('INSERT INTO usuarios (usuario, pwd_hash) VALUES (?, ?)', (usuario, pwd_hash))
        usuario_db = query_db('SELECT id FROM usuarios WHERE usuario=?', (usuario,), one=True)
        return {"status": "ok", "mensaje": "Cuenta creada", "usuario_id": usuario_db[0]}
