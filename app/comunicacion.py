import json


class Comunicacion:
    @staticmethod
    def enviar(mensaje, conn):
        try:
            mensaje_json = json.dumps(mensaje)
            print(f"Mensaje JSON a enviar: {mensaje_json}")
            conn.sendall(mensaje_json.encode('utf-8'))
        except Exception as e:
            print(f"Error al enviar el mensaje JSON: {e}")
            raise

    @staticmethod
    def recibir(conn):
        try:
            buffer_size = 4096
            data = conn.recv(buffer_size)
            if not data:
                print("No se recibieron datos.")
                return None
            mensaje_json = data.decode('utf-8')
            print(f"Mensaje recibido: {mensaje_json}")
            mensaje = json.loads(mensaje_json)
            return mensaje
        except Exception as e:
            print(f"Error al recibir el mensaje: {e}")
            return None
