import socket


class Comunicacion:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket_cliente = None

    def conectar(self):
        self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_cliente.connect((self.host, self.port))

    def enviar_datos(self, data):
        self.socket_cliente.sendall(data.encode())

    def recibir_datos(self):
        return self.socket_cliente.recv(4096).decode()

    def cerrar_conexion(self):
        if self.socket_cliente:
            self.socket_cliente.close()
            self.socket_cliente = None
