import getpass
import hashlib
import json
import random
import sys
from threading import Thread

from comunicacion import Comunicacion
from config_util import cargar_configuracion
from utils import indices_a_celda


class Cliente:
    def __init__(self, usuario):
        self.host, self.port = cargar_configuracion()
        self.usuario = usuario
        self.comunicacion = Comunicacion(self.host, self.port)
        self.hoja_de_calculo = []
        self.activo = True

    def conectar_servidor(self):
        self.comunicacion.conectar()

    def enviar_credenciales(self):
        pwd = getpass.getpass("Contraseña: ")
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        mensaje = json.dumps({"usuario": self.usuario, "pwd": pwd})
        self.comunicacion.enviar_datos(mensaje)
        respuesta = self.comunicacion.recibir_datos()
        respuesta_dict = json.loads(respuesta)
        if "error" in respuesta_dict:
            print(f"Error del servidor: {respuesta_dict['error']}")
            sys.exit(1)
        elif respuesta_dict["status"] == "OK":
            self.hojas_usuario = respuesta_dict["hojas"]
        else:
            print("Error desconocido.")
            sys.exit(1)

    def mostrar_menu_y_elegir_hoja(self):
        print(f"Hojas de cálculo disponibles: {self.hojas_usuario}")
        print("Elija una opción:")
        print("1. Crear nueva hoja de cálculo")
        print("2. Seleccionar hoja de cálculo existente")
        print("3. Compartir hoja de cálculo")
        opcion = input("Ingrese el número de la opción deseada: ")

        if opcion == "1":
            return self.crear_nueva_hoja()
        elif opcion == "2":
            return self.seleccionar_hoja_existente()
        elif opcion == "3":
            return self.compartir_hoja()
        else:
            print("Opción no válida. Saliendo...")
            sys.exit(1)

    def crear_nueva_hoja(self):
        nombre_hoja = input("Ingrese el nombre para la nueva hoja de cálculo: ")
        mensaje = json.dumps({"opcion": "nueva", "nombre_hoja": nombre_hoja})
        self.comunicacion.enviar_datos(mensaje)
        return self.recibir_hoja_completa(nombre_hoja)

    def seleccionar_hoja_existente(self):
        if not self.hojas_usuario:
            print("No tiene hojas de cálculo existentes.")
            return self.mostrar_menu_y_elegir_hoja()

        print("Hojas de cálculo disponibles:")
        for i, hoja in enumerate(self.hojas_usuario, start=1):
            print(f"{i}. {hoja}")
        opcion = int(input("Seleccione el número de la hoja de cálculo: "))
        if 1 <= opcion <= len(self.hojas_usuario):
            nombre_hoja = self.hojas_usuario[opcion - 1]
            mensaje = json.dumps({"opcion": "existente", "nombre_hoja": nombre_hoja})
            self.comunicacion.enviar_datos(mensaje)
            return self.recibir_hoja_completa(nombre_hoja)
        else:
            print("Opción no válida.")
            return self.mostrar_menu_y_elegir_hoja()

    def compartir_hoja(self):
        if not self.hojas_usuario:
            print("No tiene hojas de cálculo existentes para compartir.")
            return self.mostrar_menu_y_elegir_hoja()

        print("Hojas de cálculo disponibles:")
        for i, hoja in enumerate(self.hojas_usuario, start=1):
            print(f"{i}. {hoja}")
        opcion = int(input("Seleccione el número de la hoja de cálculo que desea compartir: "))
        if 1 <= opcion <= len(self.hojas_usuario):
            nombre_hoja = self.hojas_usuario[opcion - 1]
            usuario_a_compartir = input("Ingrese el nombre del usuario con quien desea compartir la hoja: ")
            mensaje = json.dumps(
                {"opcion": "compartir", "nombre_hoja": nombre_hoja, "usuario_compartido": usuario_a_compartir})
            self.comunicacion.enviar_datos(mensaje)
            respuesta = self.comunicacion.recibir_datos()
            respuesta_dict = json.loads(respuesta)
            if "error" in respuesta_dict:
                print(f"Error del servidor: {respuesta_dict['error']}")
            else:
                print(f"Hoja de cálculo '{nombre_hoja}' compartida con éxito con el usuario '{usuario_a_compartir}'.")
        else:
            print("Opción no válida.")
            return self.mostrar_menu_y_elegir_hoja()

        self.cerrar_conexion()
        sys.exit(0)

    def recibir_hoja_completa(self, nombre_hoja):
        datos = self.comunicacion.recibir_datos()
        hoja_recibida = json.loads(datos)

        if "error" in hoja_recibida:
            print(f"Error recibido del servidor: {hoja_recibida['error']}")
            sys.exit(1)

        self.hoja_de_calculo = hoja_recibida
        print("Hoja de cálculo recibida:")
        for fila in self.hoja_de_calculo:
            print(",".join(fila))

        return nombre_hoja

    def iniciar_interaccion(self, nombre_hoja):
        actualizacion_thread = Thread(target=self.recibir_actualizaciones)
        actualizacion_thread.start()

        try:
            while self.activo:
                fila = random.randint(1, 5)
                columna = random.randint(1, 5)
                celda = indices_a_celda(fila, columna)
                valor = input(f"Ingrese el valor para {celda}: ")
                self.actualizar_celda(nombre_hoja, celda, valor)
        except KeyboardInterrupt:
            self.detener_cliente()
        finally:
            self.detener_cliente()

    def actualizar_celda(self, nombre_hoja, celda, valor):
        mensaje = json.dumps({"nombre_hoja": nombre_hoja, "celda": celda, "valor": valor})
        self.comunicacion.enviar_datos(mensaje)

    def detener_cliente(self):
        self.activo = False
        self.cerrar_conexion()

    def cerrar_conexion(self):
        self.comunicacion.cerrar_conexion()

    def recibir_actualizaciones(self):
        while self.activo:
            try:
                datos = self.comunicacion.recibir_datos()
                if not datos:
                    break
                print("\nActualización recibida:", datos)
            except OSError:
                if self.activo:
                    break


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 cliente.py <usuario>")
    else:
        cliente = Cliente(sys.argv[1])
        cliente.conectar_servidor()
        cliente.enviar_credenciales()
        nombre_hoja = cliente.mostrar_menu_y_elegir_hoja()
        cliente.iniciar_interaccion(nombre_hoja)
