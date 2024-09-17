import csv
import logging
import os
import re
import select
import socket
import threading

from tabulate import tabulate

from comunicacion import Comunicacion
from utils import evaluar_expresion


class HojaCalculo:
    def __init__(self, sesion):
        self.sesion = sesion
        self.hoja_editada_id = None
        self.lista_hojas = []
        self.dict_celdas_hoja = {}
        self.lock = threading.Lock()
        self.event_edicion = threading.Event()

    def _enviar_mensaje(self, mensaje):
        respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)
        if respuesta.get("status") != "ok":
            logging.error(f"Error al enviar mensaje: {respuesta.get('mensaje')}")
        return respuesta

    def _obtener_hojas(self):
        mensaje = {"accion": "listar_hojas", "usuario_id": self.sesion.usuario_id}
        respuesta = self._enviar_mensaje(mensaje)
        if respuesta.get("status") == "ok":
            self.lista_hojas = respuesta.get("hojas_creadas") + respuesta.get(
                "hojas_lectura_escritura") + respuesta.get("hojas_solo_lectura")
        else:
            logging.error("Error obteniendo las hojas de calculo")

    def listar_hojas(self):
        self._obtener_hojas()
        if self.lista_hojas:
            headers = ["#", "Nombre", "Creador"]
            tabla_hojas = [[i + 1, hoja[1], hoja[-1]] for i, hoja in enumerate(self.lista_hojas)]
            print("\n", tabulate(tabla_hojas, headers, tablefmt="github"))
        else:
            print("No tienes hojas de calculo")

    def crear_hoja(self):
        nombre = input("Nombre de la hoja de calculo: ")
        mensaje = {"accion": "crear_hoja", "nombre": nombre, "usuario_id": self.sesion.usuario_id}
        respuesta = self._enviar_mensaje(mensaje)
        if respuesta.get("status") == "ok":
            self.editar_o_ver_hoja(respuesta.get("hoja_id"))

    def _seleccionar_hoja(self, prompt):
        self._obtener_hojas()
        if not self.lista_hojas:
            print("No tienes hojas de calculo")
            return None
        try:
            indice = int(input(prompt)) - 1
            if 0 <= indice < len(self.lista_hojas):
                return self.lista_hojas[indice]
            print("Seleccion no valida")
        except ValueError:
            print("Opcion no valida. Debes ingresar un numero")
        return None

    def seleccionar_hoja(self):
        hoja_seleccionada = self._seleccionar_hoja("Selecciona el id de hoja: ")
        if hoja_seleccionada:
            hoja_id = hoja_seleccionada[0]
            if hoja_id:
                self.editar_o_ver_hoja(hoja_id)

    def editar_o_ver_hoja(self, hoja_id):
        permisos_respuesta = self.obtener_permisos_usuario(hoja_id)
        if permisos_respuesta.get("status") != "ok":
            return

        permisos = permisos_respuesta.get("permisos")
        es_editable = permisos in ["lectura y escritura", "propietario"]

        if permisos not in ["lectura y escritura", "propietario", "solo lectura"]:
            print("No tienes permisos para editar esta hoja")
            return

        self.hoja_editada_id = hoja_id
        self.dict_celdas_hoja = {}

        respuesta = self.leer_datos_csv(hoja_id)
        if respuesta.get("status") == "ok":
            self.imprimir_hoja_calculo()

        self.event_edicion.clear()

        hilo_actualizaciones = threading.Thread(target=self.manejar_actualizaciones)
        hilo_actualizaciones.start()

        try:
            if es_editable:
                self._editar_hoja(hoja_id)
            else:
                self._ver_hoja_solo_lectura()
        except KeyboardInterrupt:
            logging.info("Edicion de hoja finalizada")
        finally:
            self.event_edicion.set()
            hilo_actualizaciones.join()
            self.hoja_editada_id = None

    def _editar_hoja(self, hoja_id):
        while not self.event_edicion.is_set():
            celda = input("Celda: ").strip().upper()
            if not re.match(r'^[A-Za-z]\d+$', celda):
                print("Formato no valido")
                continue

            valor = input("Valor: ").strip()
            valor_evaluado = evaluar_expresion(valor)

            mensaje = {"accion": "editar_celda", "hoja_id": hoja_id, "celda": celda, "valor": valor_evaluado,
                       "usuario_id": self.sesion.usuario}
            Comunicacion.enviar_mensaje(mensaje, self.sesion.sock)

    def _ver_hoja_solo_lectura(self):
        while not self.event_edicion.is_set():
            continue

    def compartir_hoja(self):
        hoja_seleccionada = self._seleccionar_hoja("Selecciona el id de hoja para compartir: ")
        if hoja_seleccionada:
            hoja_id = hoja_seleccionada[0]
            permisos_respuesta = self.obtener_permisos_usuario(hoja_id)

            if permisos_respuesta.get("status") != "ok":
                return

            if permisos_respuesta.get("permisos") == "propietario":
                nombre_usuario = input("Usuario con quien quieres compartir el archivo: ")
                permisos = "lectura y escritura" if input(
                    "Tipo de acceso (1: Solo lectura, 2: Lectura y escritura): ") == '2' else "solo lectura"
                mensaje = {"accion": "compartir_hoja", "hoja_id": hoja_id, "nombre_usuario": nombre_usuario,
                           "permisos": permisos}
                self._enviar_mensaje(mensaje)
            else:
                print("No tienes permisos suficientes para compartir esta hoja")

    def descargar_hoja(self):
        hoja_seleccionada = self._seleccionar_hoja("Selecciona el id de hoja para descargar: ")
        if hoja_seleccionada:
            hoja_id = hoja_seleccionada[0]
            if hoja_id:
                mensaje = {"accion": "descargar_hoja", "hoja_id": hoja_id}
                respuesta = self._enviar_mensaje(mensaje)
                if respuesta.get("status") == "ok":
                    self.guardar_csv(respuesta.get("contenido_csv"), hoja_seleccionada[1])

    @staticmethod
    def guardar_csv(contenido_csv, hoja_nombre):
        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        nombre_archivo = os.path.join(downloads_path, f"{hoja_nombre}.csv")

        try:
            filas = [line.split(',') for line in contenido_csv.strip().split('\n')]
            with open(nombre_archivo, 'w', newline='') as archivo:
                csv.writer(archivo).writerows(filas)
            print(f"Hoja de calculo descargada en {nombre_archivo}")
        except Exception as e:
            logging.error(f"Error al guardar el archivo CSV: {e}")

    def eliminar_hoja(self):
        hoja_seleccionada = self._seleccionar_hoja("Selecciona el id de hoja para eliminar: ")
        if hoja_seleccionada:
            hoja_id = hoja_seleccionada[0]
            permisos_respuesta = self.obtener_permisos_usuario(hoja_id)

            if permisos_respuesta.get("status") != "ok":
                return

            if permisos_respuesta.get("permisos") == "propietario":
                mensaje = {"accion": "eliminar_hoja", "hoja_id": hoja_id, "usuario_id": self.sesion.usuario_id}
                self._enviar_mensaje(mensaje)
                print("Hoja eliminada correctamente")
            else:
                print("No tienes permisos suficientes para eliminar esta hoja")

    def obtener_permisos_usuario(self, hoja_id):
        mensaje = {"accion": "obtener_permisos", "hoja_id": hoja_id, "usuario_id": self.sesion.usuario_id}
        return self._enviar_mensaje(mensaje)

    def manejar_actualizaciones(self):
        try:
            while not self.event_edicion.is_set():
                readable, _, _ = select.select([self.sesion.sock], [], [], 1)
                if readable:
                    respuesta = Comunicacion.recibir_mensaje(self.sesion.sock)
                    if respuesta and respuesta.get("accion") == "actualizar_celda" and respuesta.get(
                            "hoja_id") == self.hoja_editada_id:
                        with self.lock:
                            self.dict_celdas_hoja[respuesta.get("celda")] = respuesta.get("valor")
                        self.imprimir_hoja_calculo()
        except (socket.error, ConnectionResetError, OSError) as e:
            logging.error(f"Error: El servidor se desconecto inesperadamente. {e}")
        finally:
            logging.info("Hilo de actualizaciones terminado")

    def leer_datos_csv(self, hoja_id):
        mensaje = {"accion": "leer_datos_csv", "hoja_id": hoja_id, "usuario_id": self.sesion.usuario_id}
        respuesta = self._enviar_mensaje(mensaje)
        if respuesta.get("status") == "ok":
            self.dict_celdas_hoja = {f"{chr(65 + j)}{i + 1}": valor for i, fila in enumerate(respuesta.get("datos")) for
                                     j, valor in enumerate(fila)}
            return {"status": "ok", "datos": respuesta.get("datos")}
        return {"status": "error"}

    def imprimir_hoja_calculo(self):
        if not self.dict_celdas_hoja:
            return
        max_fila = max(int(celda[1:]) for celda in self.dict_celdas_hoja)
        datos = [["" for _ in range(max(ord(c[0]) for c in self.dict_celdas_hoja) - 64)] for _ in range(max_fila)]
        for celda, valor in self.dict_celdas_hoja.items():
            datos[int(celda[1:]) - 1][ord(celda[0]) - 65] = valor

        columnas = [""] + [chr(65 + i) for i in range(len(datos[0]))]
        filas = [[str(i + 1)] + datos[i] for i in range(len(datos))]
        print("\n", tabulate(filas, headers=columnas, tablefmt="github"))
