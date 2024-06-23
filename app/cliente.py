import json
import os
import random
import sys
from threading import Thread

from comunicacion import Comunicacion
from utils import celda_a_indices, indices_a_celda


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
        self.hoja_de_calculo = {}

    def conectar_servidor(self):
        self.comunicacion.conectar()
        self.comunicacion.enviar_datos(f"{self.usuario},{self.hoja_nombre}")
        self.recibir_hoja_completa()

    def recibir_hoja_completa(self):
        datos = self.comunicacion.recibir_datos()
        hoja_recibida = json.loads(datos)

        # Inicializa la estructura de la hoja de cálculo
        self.hoja_de_calculo = []
        for fila in hoja_recibida:
            self.hoja_de_calculo.append(fila)

        print("Hoja de cálculo recibida:")
        for fila in self.hoja_de_calculo:
            print(",".join(fila))

    def cerrar_conexion(self):
        self.comunicacion.cerrar_conexion()

    def actualizar_celda(self, celda, valor):
        mensaje = f"{self.usuario},{celda},{valor}"
        self.comunicacion.enviar_datos(mensaje)

    def recibir_actualizaciones(self):
        while True:
            try:
                datos = self.comunicacion.recibir_datos()
                actualizacion = json.loads(datos)
                hoja_nombre = actualizacion["hoja_nombre"]
                celda = actualizacion["celda"]
                valor = actualizacion["valor"]

                if hoja_nombre == self.hoja_nombre:
                    fila, columna = celda_a_indices(celda)
                    while len(self.hoja_de_calculo) < fila:
                        self.hoja_de_calculo.append([""] * len(self.hoja_de_calculo[0]))

                    while len(self.hoja_de_calculo[fila - 1]) < columna:
                        for fila_datos in self.hoja_de_calculo:
                            fila_datos.append("")

                    self.hoja_de_calculo[fila - 1][columna - 1] = valor
                    print(f"\n>>>Actualización recibida: {celda} {valor}")
            except Exception as e:
                print(f"Error recibiendo actualización: {e}")
                break

    def iniciar_interaccion(self):
        actualizacion_thread = Thread(target=self.recibir_actualizaciones)
        actualizacion_thread.start()

        try:
            while True:
                fila = random.randint(1, 3)
                columna = random.randint(1, 3)
                celda = indices_a_celda(fila, columna)
                valor = input(f"Ingrese el valor para {celda}: ")

                self.actualizar_celda(celda, valor)
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
