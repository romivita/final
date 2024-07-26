import getpass
import hashlib
import json
import os
import random
import sys
from threading import Thread

from comunicacion import Comunicacion
from config_util import cargar_configuracion
from utils import indices_a_celda, safe_eval


class Cliente:
    def __init__(self, usuario):
        self.host, self.port = cargar_configuracion()
        self.usuario = usuario
        self.comunicacion = Comunicacion(self.host, self.port)
        self.hoja_de_calculo = []
        self.activo = True
        self.hojas_usuario = {}

    def conectar_servidor(self):
        self.comunicacion.conectar()

    def enviar_credenciales(self):
        mensaje = json.dumps({"usuario": self.usuario, "accion": "verificar"})
        self.comunicacion.enviar_datos(mensaje)
        respuesta = self.comunicacion.recibir_datos()
        respuesta_dict = json.loads(respuesta)
        if "error" in respuesta_dict:
            print(f"Error del servidor: {respuesta_dict['error']}")
            sys.exit(1)

        if respuesta_dict["status"] == "no_existe":
            print("Nueva cuenta.")
            pwd = getpass.getpass("Contraseña: ")
            pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
            mensaje_creacion = json.dumps({"crear_nuevo_usuario": True, "usuario": self.usuario, "pwd": pwd_hash})
            self.comunicacion.enviar_datos(mensaje_creacion)
            respuesta = self.comunicacion.recibir_datos()
            respuesta_dict = json.loads(respuesta)
            if "error" in respuesta_dict:
                print(f"Error del servidor: {respuesta_dict['error']}")
                sys.exit(1)
            if respuesta_dict["status"] == "nuevo_usuario_creado":
                print("Usuario creado exitosamente.")
            else:
                print("Error desconocido.")
                sys.exit(1)

        elif respuesta_dict["status"] == "existe":
            pwd = getpass.getpass("Contraseña: ")
            pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
            mensaje = json.dumps({"usuario": self.usuario, "pwd": pwd_hash})
            self.comunicacion.enviar_datos(mensaje)
            respuesta = self.comunicacion.recibir_datos()
            respuesta_dict = json.loads(respuesta)
            if "error" in respuesta_dict:
                print(f"Error del servidor: {respuesta_dict['error']}")
                sys.exit(1)
            elif respuesta_dict["status"] == "OK":
                self.hojas_usuario = {hoja['id']: hoja['nombre'] for hoja in respuesta_dict["hojas"]}
            else:
                print("Error desconocido.")
                sys.exit(1)

    def mostrar_menu_y_elegir_hoja(self):
        while True:
            if not self.hojas_usuario:
                print("No tiene hojas de calculo disponibles.")
            else:
                nombres_hojas = list(self.hojas_usuario.values())
                print(f"Hojas de cálculo disponibles: {', '.join(nombres_hojas)}")
            print("Elija una opción:")
            print("1. Crear nueva hoja de calculo")
            if self.hojas_usuario:
                print("2. Seleccionar hoja de calculo existente")
                print("3. Compartir hoja de calculo")
                print("4. Descargar hoja de calculo en formato CSV")
            opcion = input("Ingrese el número de la opción deseada: ")

            if opcion == "1":
                return self.crear_nueva_hoja()
            elif opcion == "2":
                return self.seleccionar_hoja_existente()
            # elif opcion == "3":
            #     self.compartir_hoja()
            elif opcion == "4":
                self.descargar_hoja_csv()
            else:
                print("Opción no válida. Intente de nuevo.")

    def crear_nueva_hoja(self):
        nombre_hoja = input("Ingrese el nombre para la nueva hoja de calculo: ")
        mensaje = json.dumps({"opcion": "nueva", "nombre_hoja": nombre_hoja})
        self.comunicacion.enviar_datos(mensaje)

        respuesta = self.comunicacion.recibir_datos()
        print(f"Respuesta del servidor al crear hoja: {respuesta}")

        try:
            respuesta_json = json.loads(respuesta)
            if 'status' in respuesta_json and respuesta_json['status'] == 'OK':
                nueva_hoja_id = respuesta_json.get('hoja_id')
                print(f"Hoja de calculo creada con ID: {respuesta_json['hoja_id']}")

                self.asignar_permisos_cliente(nueva_hoja_id)

                compartir = input("¿Desea compartir esta hoja de calculo? (s/n): ").strip().lower()
                if compartir == 's':
                    self.compartir_hoja(nueva_hoja_id)
                return nueva_hoja_id
            else:
                print("Error al crear la hoja de calculo.")
        except json.JSONDecodeError as e:
            print(f"Error al decodificar la respuesta JSON: {e}")

    def asignar_permisos_cliente(self, hoja_id):
        mensaje = json.dumps({"opcion": "registrar", "hoja_id": f"{hoja_id}"})
        self.comunicacion.enviar_datos(mensaje)

    def seleccionar_hoja_existente(self):
        if not self.hojas_usuario:
            print("No tiene hojas de calculo existentes.")
            return self.mostrar_menu_y_elegir_hoja()

        while True:
            print("Hojas de calculo disponibles:")
            for i, (hoja_id, nombre) in enumerate(self.hojas_usuario.items(), start=1):
                print(f"{i}. {nombre}")
            opcion = input("Seleccione el número de la hoja de calculo: ")
            if opcion.isdigit():
                opcion = int(opcion)
                if 1 <= opcion <= len(self.hojas_usuario):
                    hoja_id = list(self.hojas_usuario.keys())[opcion - 1]
                    mensaje = json.dumps({"opcion": "existente", "hoja_id": f"{hoja_id}"})
                    print(f"Enviando mensaje para seleccionar hoja existente: {mensaje}")  # Mensaje de depuración
                    self.comunicacion.enviar_datos(mensaje)
                    return hoja_id
            print("Opción no válida. Intente de nuevo.")

    def compartir_hoja(self, hoja_id):
        usuario_a_compartir = input("Ingrese el nombre del usuario con quien desea compartir la hoja: ")
        mensaje = json.dumps(
            {"opcion": "compartir", "hoja_id": f"{hoja_id}", "usuario_compartido": usuario_a_compartir})
        self.comunicacion.enviar_datos(mensaje)
        respuesta = self.comunicacion.recibir_datos()
        respuesta_dict = json.loads(respuesta)
        if "error" in respuesta_dict:
            print(f"Error del servidor: {respuesta_dict['error']}")
        else:
            print(
                f"Hoja de calculo '{self.hojas_usuario[hoja_id]}' compartida con éxito con el usuario '{usuario_a_compartir}'.")

    def descargar_hoja_csv(self):
        if not self.hojas_usuario:
            print("No tiene hojas de calculo existentes para descargar.")
            return
        while True:
            print("Hojas de calculo disponibles:")
            for i, (hoja_id, nombre) in enumerate(self.hojas_usuario.items(), start=1):
                print(f"{i}. {nombre}")
            opcion = input("Seleccione el número de la hoja de calculo que desea descargar: ")
            if opcion.isdigit():
                opcion = int(opcion)
                if 1 <= opcion <= len(self.hojas_usuario):
                    hoja_id = list(self.hojas_usuario.keys())[opcion - 1]
                    mensaje = json.dumps({"opcion": "descargar", "hoja_id": f"{hoja_id}"})
                    self.comunicacion.enviar_datos(mensaje)
                    respuesta = self.comunicacion.recibir_datos()
                    try:
                        respuesta_dict = json.loads(respuesta)
                    except json.JSONDecodeError as e:
                        print(f"Error al decodificar la respuesta JSON: {e}")
                        return
                    if "error" in respuesta_dict:
                        print(f"Error del servidor: {respuesta_dict['error']}")
                    else:
                        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
                        file_path = os.path.join(downloads_path, f"{self.hojas_usuario[hoja_id]}.csv")
                        file = open(file_path, "w")
                        try:
                            file.write(respuesta_dict["csv"])
                        finally:
                            file.close()
                        print(f"Hoja de calculo '{self.hojas_usuario[hoja_id]}' descargada con éxito en '{file_path}'.")
                    return
            print("Opción no válida. Intente de nuevo.")

    def recibir_hoja_completa(self):
        datos = self.comunicacion.recibir_datos().strip()  # Eliminar delimitadores innecesarios
        print(f"Datos recibidos para la hoja completa: {datos}")  # Mensaje de depuración
        try:
            hoja_recibida = json.loads(datos)
        except json.JSONDecodeError as e:
            print(f"Error al decodificar la respuesta JSON: {e}")
            sys.exit(1)

        if "error" in hoja_recibida:
            print(f"Error recibido del servidor: {hoja_recibida['error']}")
            sys.exit(1)

        self.hoja_de_calculo = hoja_recibida["datos"]

        for fila in self.hoja_de_calculo:
            print(",".join(fila))

    def iniciar_thread_cliente(self, hoja_id):
        actualizacion_thread = Thread(target=self.recibir_actualizaciones)
        actualizacion_thread.start()
        try:
            while self.activo:
                fila = random.randint(1, 5)
                columna = random.randint(1, 5)
                celda = indices_a_celda(fila, columna)
                valor = input(f"Ingrese el valor para {celda}: ")
                self.actualizar_celda(hoja_id, celda, valor)
        except KeyboardInterrupt:
            self.detener_cliente()
        finally:
            self.detener_cliente()

    def actualizar_celda(self, hoja_id, celda, valor):
        if valor.startswith('='):
            try:
                resultado = safe_eval(valor[1:])
                valor = str(resultado)
            except Exception as e:
                print(f"Error al evaluar la fórmula: {e}")
                return
        mensaje = json.dumps({"hoja_id": f"{hoja_id}", "celda": celda, "valor": valor})
        print(f"Enviando actualización de celda: {mensaje}")
        self.comunicacion.enviar_datos(mensaje)

    def recibir_actualizaciones(self):
        while self.activo:
            try:
                actualizacion = self.comunicacion.recibir_datos()
                if actualizacion:
                    actualizacion = json.loads(actualizacion)
                    print("\nActualización recibida:")
                    print(actualizacion)
            except json.JSONDecodeError as e:
                print(f"Error al decodificar la actualización JSON: {e}")
            except OSError:
                if self.activo:
                    break

    def detener_cliente(self):
        self.activo = False
        self.comunicacion.cerrar_conexion()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 cliente.py <usuario>")
    else:
        cliente = Cliente(sys.argv[1])
        cliente.conectar_servidor()
        cliente.enviar_credenciales()
        hoja_id = cliente.mostrar_menu_y_elegir_hoja()
        cliente.iniciar_thread_cliente(hoja_id)
