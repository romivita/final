import json
import logging
import socket


def manejar_excepciones(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (socket.error, ConnectionError, ConnectionResetError, BrokenPipeError, OSError) as e:
            logging.error(f"Socket error en {func.__name__}: {e}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Error al decodificar JSON en {func.__name__}: {e}")
            raise ValueError("El mensaje recibido no es un JSON valido")
        except ValueError as e:
            logging.error(f"ValueError en {func.__name__}: {e}")
            raise
        except Exception as e:
            logging.error(f"Error inesperado en {func.__name__}: {e}")
            raise

    return wrapper


class Comunicacion:

    @staticmethod
    @manejar_excepciones
    def enviar_mensaje(mensaje, conn):
        if not isinstance(mensaje, dict):
            raise ValueError("El mensaje a enviar debe ser un diccionario")

        if mensaje is None:
            raise ValueError("El mensaje a enviar no puede ser None")

        mensaje_json = json.dumps(mensaje)

        if conn is None:
            raise ConnectionError("La conexion es None, no se puede enviar el mensaje")

        conn.sendall(mensaje_json.encode('utf-8'))
        logging.info(f"{mensaje_json}")

    @staticmethod
    @manejar_excepciones
    def recibir_mensaje(conn, buffer_size=4096):
        if conn is None:
            raise ConnectionError("La conexion es None, no se puede recibir el mensaje")

        data = conn.recv(buffer_size)
        if not data:
            raise ConnectionError("No se recibieron datos, posible desconexion")

        mensaje_json = data.decode('utf-8')
        mensaje = json.loads(mensaje_json)
        logging.info(f"{mensaje_json}")
        return mensaje

    @staticmethod
    @manejar_excepciones
    def enviar_y_recibir(mensaje, conn, buffer_size=4096):
        Comunicacion.enviar_mensaje(mensaje, conn)
        return Comunicacion.recibir_mensaje(conn, buffer_size)
