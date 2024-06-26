import json
import os
import sys

from comunicacion import Comunicacion


class Cliente:
    def __init__(self, usuario, hoja_nombre):
        ruta_config = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fixtures/config.json'))
        file = open(ruta_config, "r")
        try:
            config = json.load(file)
            self.host = config["host"]
            self.port = config["port"]
        finally:
            file.close()

        self.usuario = usuario
        self.hoja_nombre = hoja_nombre
        self.comunicacion = Comunicacion(self.host, self.port)

    def conectar_servidor(self):
        self.comunicacion.conectar()
        self.comunicacion.enviar_datos(f"{self.usuario},{self.hoja_nombre}")
        self.mostrar_contenido_inicial()

    def mostrar_contenido_inicial(self):
        print("Contenido inicial:")
        while True:
            data = self.comunicacion.recibir_datos().strip()
            if not data:
                break
            print(data)

    def cerrar_conexion(self):
        self.comunicacion.cerrar_conexion()

    def actualizar_celda(self, fila, columna, valor):
        mensaje = f"{self.usuario},{fila},{columna},{valor}"
        self.comunicacion.enviar_datos(mensaje)

    def iniciar_interaccion(self):
        try:
            while True:
                fila = int(input("Ingrese número de fila: "))
                columna = int(input("Ingrese número de columna: "))
                valor = input("Ingrese el valor: ")

                self.actualizar_celda(fila, columna, valor)
        except KeyboardInterrupt:
            print("Cerrando conexión...")
        finally:
            self.cerrar_conexion()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 cliente.py <usuario> <nombre_hoja_calculo>")
    else:
        cliente = Cliente(sys.argv[1], sys.argv[2])
        cliente.conectar_servidor()
        cliente.iniciar_interaccion()
