import json
import os
import random
import sys
from threading import Thread

from comunicacion import Comunicacion


def letra_a_indice(letra):
    """Convierte una letra de columna a un índice numérico (A=1, B=2, ...)"""
    return ord(letra.upper()) - ord('A') + 1


def indice_a_letra(indice):
    """Convierte un índice numérico a una letra de columna (1=A, 2=B, ...)"""
    return chr(indice + ord('A') - 1)


def celda_a_indices(celda):
    """Convierte una referencia de celda (p.ej., 'A1') a índices de fila y columna (p.ej., (1, 1))"""
    columna = letra_a_indice(celda[0])
    fila = int(celda[1:])
    return fila, columna


def indices_a_celda(fila, columna):
    """Convierte índices de fila y columna a una referencia de celda (p.ej., (1, 1) a 'A1')"""
    letra_columna = indice_a_letra(columna)
    return f"{letra_columna}{fila}"


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
        fila, columna = celda_a_indices(celda)
        mensaje = f"{self.usuario},{fila},{columna},{valor}"
        self.comunicacion.enviar_datos(mensaje)

    def recibir_actualizaciones(self):
        while True:
            try:
                datos = self.comunicacion.recibir_datos()
                actualizacion = json.loads(datos)
                hoja_nombre = actualizacion["hoja_nombre"]
                fila = actualizacion["fila"]
                columna = actualizacion["columna"]
                valor = actualizacion["valor"]

                if hoja_nombre == self.hoja_nombre:
                    while len(self.hoja_de_calculo) < fila:
                        self.hoja_de_calculo.append([""] * len(self.hoja_de_calculo[0]))

                    while len(self.hoja_de_calculo[fila - 1]) < columna:
                        for fila_datos in self.hoja_de_calculo:
                            fila_datos.append("")

                    self.hoja_de_calculo[fila - 1][columna - 1] = valor
                    celda = indices_a_celda(fila, columna)
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
