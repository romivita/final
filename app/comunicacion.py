import socket


class Comunicacion:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def conectar(self):
        self.socket_cliente.connect((self.host, self.port))

    def enviar_datos(self, datos):
        self.socket_cliente.sendall(datos.encode('utf-8'))

    def recibir_datos(self):
        return self.socket_cliente.recv(4096).decode('utf-8')

    def cerrar_conexion(self):
        self.socket_cliente.close()
