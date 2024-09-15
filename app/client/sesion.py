import getpass
import logging
import socket
import sys
import threading

from comunicacion import Comunicacion


class Sesion:
    def __init__(self, usuario, host, port):
        self.usuario = usuario
        self.host = host
        self.port = port
        self.sock = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.stop_edicion = threading.Event()

        self.conectar_servidor()
        self.usuario_id = self.autenticar_usuario()

    def conectar_servidor(self):
        for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            familia, tipo, proto, canonname, sockaddr = res
            try:
                self.sock = socket.socket(familia, tipo, proto)
                self.sock.connect(sockaddr)
                break
            except socket.error:
                if self.sock:
                    self.sock.close()
                    self.sock = None
        if self.sock is None:
            sys.exit(f"No se pudo conectar al servidor en {self.host}:{self.port}.")

    def autenticar_usuario(self):
        pwd = getpass.getpass("Contraseña: ")
        mensaje = {"accion": "iniciar_sesion", "usuario": self.usuario, "pwd": pwd}
        respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sock)
        return self._validar_autenticacion(respuesta)

    def _validar_autenticacion(self, respuesta):
        if respuesta.get("status") == "ok":
            return respuesta["usuario_id"]
        sys.exit("Error de autenticacion. Saliendo...")

    def desconectar(self):
        if self.sock:
            try:
                mensaje = {"accion": "desconectar"}
                Comunicacion.enviar_mensaje(mensaje, self.sock)
            except Exception as e:
                logging.exception(f"Error al enviar mensaje de desconexion: {e}")
            finally:
                self._cerrar_sesion()

    def _cerrar_sesion(self):
        self.stop_event.set()
        self.stop_edicion.set()
        if self.sock:
            self.sock.close()
        logging.info("Cliente desconectado")
