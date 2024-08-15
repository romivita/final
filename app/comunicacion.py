import json


class Comunicacion:
    @staticmethod
    def enviar_mensaje(mensaje, conn):
        try:
            mensaje_json = json.dumps(mensaje)
            conn.sendall(mensaje_json.encode('utf-8'))
        except Exception as e:
            print(f"Error al enviar el mensaje JSON: {e}")
            raise

    @staticmethod
    def recibir_mensaje(conn, buffer_size=4096):
        try:
            data = conn.recv(buffer_size)
            if not data:
                print("No se recibieron datos.")
                return None
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            print(f"Error al recibir el mensaje: {e}")
            return None

    @staticmethod
    def enviar_y_recibir(mensaje, conn, buffer_size=4096):
        Comunicacion.enviar_mensaje(mensaje, conn)
        return Comunicacion.recibir_mensaje(conn, buffer_size)
