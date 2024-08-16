import getpass
import socket
import sys
import threading

from comunicacion import Comunicacion
from config_util import cargar_configuracion


class Sesion:
    def __init__(self, usuario):
        self.usuario = usuario
        self.host, self.port = cargar_configuracion()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        try:
            self.sock.connect((self.host, self.port))
        except ConnectionRefusedError:
            sys.exit(f"No se pudo conectar al servidor en {self.host}:{self.port}. "
                     "Asegúrate de que el servidor esté corriendo e inténtalo nuevamente.")

        self.usuario_id = self.autenticar_usuario()

    def autenticar_usuario(self):
        pwd = getpass.getpass("Contraseña: ")
        mensaje = {"accion": "iniciar_sesion", "usuario": self.usuario, "pwd": pwd}
        respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sock)
        if respuesta["status"] == "ok":
            return respuesta["usuario_id"]
        else:
            sys.exit("Error de autenticación. Saliendo...")

    def desconectar(self):
        try:
            mensaje = {"accion": "desconectar"}
            Comunicacion.enviar_mensaje(mensaje, self.sock)
        except Exception as e:
            print(f"Error al enviar mensaje de desconexión: {e}")
        finally:
            self.sock.close()
