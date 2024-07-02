import json
import random
import sys
from threading import Thread

from comunicacion import Comunicacion
from config_util import cargar_configuracion
from utils import celda_a_indices, indices_a_celda


class Cliente:
    def __init__(self, usuario, nombre_hoja):
        self.host, self.port = cargar_configuracion()
        self.usuario = usuario
        self.nombre_hoja = nombre_hoja
        self.comunicacion = Comunicacion(self.host, self.port)
        self.hoja_de_calculo = []

    def conectar_servidor(self):
        self.comunicacion.conectar()
        self.comunicacion.enviar_datos(f"{self.usuario},{self.nombre_hoja}")
        self.recibir_hoja_completa()

    def recibir_hoja_completa(self):
        datos = self.comunicacion.recibir_datos()
        hoja_recibida = json.loads(datos)

        # Inicializa la estructura de la hoja de cálculo
        self.hoja_de_calculo = hoja_recibida

        print("Hoja de cálculo recibida:")
        for fila in self.hoja_de_calculo:
            print(",".join(fila))

    def cerrar_conexion(self):
        self.comunicacion.cerrar_conexion()

    def actualizar_celda(self, celda, valor):
        mensaje = json.dumps({"usuario": self.usuario, "celda": celda, "valor": valor})
        self.comunicacion.enviar_datos(mensaje)

    def recibir_actualizaciones(self):
        while True:
            try:
                datos = self.comunicacion.recibir_datos()
                mensaje = json.loads(datos)

                if "error" in mensaje:
                    print(f"Error recibido del servidor: {mensaje['error']}")
                    continue

                nombre_hoja = mensaje.get("nombre_hoja")
                celda = mensaje.get("celda")
                valor = mensaje.get("valor")

                if nombre_hoja == self.nombre_hoja and celda and valor is not None:
                    fila, columna = celda_a_indices(celda)
                    while len(self.hoja_de_calculo) < fila:
                        self.hoja_de_calculo.append([""] * len(self.hoja_de_calculo[0]))

                    while len(self.hoja_de_calculo[fila - 1]) < columna:
                        for fila_datos in self.hoja_de_calculo:
                            fila_datos.append("")

                    self.hoja_de_calculo[fila - 1][columna - 1] = valor
                    print(f"\n>>> Actualización recibida: {celda} {valor}")

                    # Imprimir CSV completo
                    print("\nHoja de cálculo actualizada:")
                    for fila in self.hoja_de_calculo:
                        print(",".join(fila))

            except json.JSONDecodeError as je:
                print(f"Error de JSON al decodificar datos: {je}")
            except Exception as e:
                print(f"Error recibiendo actualización: {e}")
                break

    def iniciar_interaccion(self):
        actualizacion_thread = Thread(target=self.recibir_actualizaciones)
        actualizacion_thread.start()

        try:
            while True:
                fila = random.randint(1, 5)
                columna = random.randint(1, 5)
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
