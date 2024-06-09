import socket


class Comunicacion:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def conectar(self):
        self.socket_cliente.connect((self.host, self.port))

    def enviar_datos(self, datos):
        self.socket_cliente.sendall(datos.encode())

    def cerrar_conexion(self):
        self.socket_cliente.close()
