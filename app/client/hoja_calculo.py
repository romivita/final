import csv
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
        self.hoja_editada = None
        self.hojas = []
        self.hoja_dict = {}
        self.update_lock = threading.Lock()
        self.stop_edicion = self.sesion.stop_edicion

    def listar_hojas(self):
        mensaje = {"accion": "listar_hojas", "usuario_id": self.sesion.usuario_id}
        respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)
        if respuesta['status'] == 'ok':
            self.hojas = respuesta['hojas_creadas'] + respuesta['hojas_lectura_escritura'] + respuesta[
                'hojas_solo_lectura']
            if self.hojas:
                headers = ["#", "Nombre", "Creador"]
                tabla_hojas = [[i + 1, hoja[1], hoja[-1]] for i, hoja in enumerate(self.hojas)]
                print(tabulate(tabla_hojas, headers, tablefmt="github"))
            else:
                print("No tienes hojas de calculo.")
        else:
            print(respuesta["mensaje"])

    def crear_hoja(self):
        nombre = input("Nombre de la hoja de calculo: ")
        mensaje = {"accion": "crear_hoja", "nombre": nombre, "usuario_id": self.sesion.usuario_id}
        respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)
        if respuesta["status"] == "ok":
            self.editar_o_ver_hoja(respuesta["hoja_id"])
        else:
            print(respuesta["mensaje"])

    def seleccionar_hoja(self):
        if not self.hojas:
            print("No tienes hojas de cálculo disponibles para editar.")
            return

        try:
            indice = int(input("Selecciona el número de hoja: ")) - 1
            if 0 <= indice < len(self.hojas):
                hoja_seleccionada = self.hojas[indice]
                hoja_id = self.obtener_hoja_id(hoja_seleccionada[1])
                if hoja_id:
                    self.editar_o_ver_hoja(hoja_id)
            else:
                print("Selección no válida.")
        except ValueError:
            print("Opción no válida. Debes ingresar un número entero.")

    def editar_o_ver_hoja(self, hoja_id):
        permisos_respuesta = self.obtener_permisos_usuario(hoja_id)
        if permisos_respuesta["status"] != "ok":
            print(permisos_respuesta["mensaje"])
            return

        permisos = permisos_respuesta.get("permisos")
        es_editable = permisos in ["lectura y escritura", "propietario"]

        if permisos not in ["lectura y escritura", "propietario", "solo lectura"]:
            print("No tienes permisos suficientes para editar esta hoja.")
            return

        self.hoja_editada = hoja_id
        self.hoja_dict = {}

        respuesta = self.leer_datos_csv(hoja_id)
        if respuesta["status"] == "ok":
            self.imprimir_hoja_calculo()

        self.stop_edicion.clear()
        hilo_actualizaciones = threading.Thread(target=self.manejar_actualizaciones, daemon=True)
        hilo_actualizaciones.start()

        try:
            if es_editable:
                self._editar_hoja(hoja_id)
            else:
                self._ver_hoja_solo_lectura()
        except KeyboardInterrupt:
            print("\nEdicion de hoja finalizada. Volviendo al menu principal...")
        finally:
            self.stop_edicion.set()
            hilo_actualizaciones.join()
            self.hoja_editada = None

    def _editar_hoja(self, hoja_id):
        while not self.stop_edicion.is_set():
            celda = input("Celda: ").strip().upper()
            if not re.match(r'^[a-zA-Z]+\d+$', celda):
                print("Formato de celda no valido. Intenta de nuevo.")
                continue

            valor = input("Valor: ").strip()
            valor_evaluado = evaluar_expresion(valor)

            mensaje = {"accion": "editar_celda", "hoja_id": hoja_id, "celda": celda, "valor": valor_evaluado,
                       "usuario_id": self.sesion.usuario_id}

            Comunicacion.enviar_mensaje(mensaje, self.sesion.sock)

    def _ver_hoja_solo_lectura(self):
        while not self.stop_edicion.is_set():
            continue

    def compartir_hoja(self):
        if not self.hojas:
            print("No tienes hojas de cálculo disponibles para editar.")
            return

        indice = int(input("Selecciona el número de hoja: ")) - 1
        if 0 <= indice < len(self.hojas):
            hoja_seleccionada = self.hojas[indice]
            hoja_id = self.obtener_hoja_id(hoja_seleccionada[1])
            if hoja_id:
                nombre_usuario = input("Nombre del usuario con quien compartir: ")
                print("Selecciona el permiso que deseas otorgar:")
                print("1. Solo lectura")
                print("2. Lectura y escritura")
                permisos = "lectura y escritura" if input("Selecciona una opcion: ") == '2' else "solo lectura"
                mensaje = {"accion": "compartir_hoja", "hoja_id": hoja_id, "nombre_usuario": nombre_usuario,
                           "permisos": permisos}
                respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)
                print(respuesta["mensaje"])

    def descargar_hoja(self):
        if not self.hojas:
            print("No tienes hojas de calculo disponibles para descargar.")
            return

        indice = int(input("Selecciona el número de hoja: ")) - 1
        if 0 <= indice < len(self.hojas):
            hoja_seleccionada = self.hojas[indice]
            hoja_nombre = hoja_seleccionada[1]
            hoja_id = self.obtener_hoja_id(hoja_seleccionada[1])
            if hoja_id:
                mensaje = {"accion": "descargar_hoja", "hoja_id": hoja_id}
                respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)
                if respuesta["status"] == "ok":
                    downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
                    nombre_archivo = os.path.join(downloads_path, f"{hoja_nombre}.csv")
                    try:
                        archivo = open(nombre_archivo, 'w', newline='')
                        try:
                            escritor = csv.writer(archivo)
                            escritor.writerows(respuesta["contenido_csv"])
                            print(f"Hoja de cálculo descargada y guardada en {nombre_archivo}")
                        except Exception as e:
                            return {"status": "error", "mensaje": f"Error al escribir en el archivo CSV: {e}"}
                        finally:
                            archivo.close()
                    except Exception as e:
                        return {"status": "error", "mensaje": f"Error al abrir el archivo CSV: {e}"}
                else:
                    print(respuesta["mensaje"])
        else:
            print("Selección no válida.")

    def eliminar_hoja(self):
        if not self.hojas:
            print("No tienes hojas de calculo disponibles.")
            return

        indice = int(input("Selecciona el número de hoja para eliminar: ")) - 1
        if 0 <= indice < len(self.hojas):
            hoja_seleccionada = self.hojas[indice]
            hoja_id = self.obtener_hoja_id(hoja_seleccionada[1])
            if hoja_id:
                mensaje = {"accion": "eliminar_hoja", "hoja_id": hoja_id, "usuario_id": self.sesion.usuario_id}
                respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)
                print(respuesta["mensaje"])
        else:
            print("Selección no válida.")

    def obtener_hoja_id(self, nombre):
        mensaje = {"accion": "obtener_hoja_id", "nombre": nombre, "usuario_id": self.sesion.usuario_id}
        respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)
        if respuesta["status"] == "ok":
            return respuesta["hoja_id"]
        else:
            print(respuesta["mensaje"])
            return None

    def obtener_permisos_usuario(self, hoja_id):
        mensaje = {"accion": "obtener_permisos", "hoja_id": hoja_id, "usuario_id": self.sesion.usuario_id}
        return Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)

    def manejar_actualizaciones(self):
        try:
            while not self.stop_edicion.is_set():
                try:
                    readable, _, _ = select.select([self.sesion.sock], [], [], 1)
                    if readable:
                        respuesta = Comunicacion.recibir_mensaje(self.sesion.sock)
                        if respuesta and respuesta.get("accion") == "actualizar_celda":
                            hoja_id = respuesta.get("hoja_id")
                            celda = respuesta.get("celda")
                            valor = respuesta.get("valor")
                            usuario_id = respuesta.get("usuario_id")
                            if hoja_id == self.hoja_editada:
                                print(
                                    f"\nActualización recibida en hoja {hoja_id}: Celda {celda} = {valor} (Usuario ID: {usuario_id})")
                                with self.update_lock:
                                    self.hoja_dict[celda] = valor
                                    self.imprimir_hoja_calculo()
                except (socket.error, ConnectionResetError, OSError) as e:
                    print(f"\nError: El servidor se desconectó inesperadamente. {e}")
                    break
        except Exception as e:
            print(f"\nError en el hilo de actualizaciones: {e}")
        finally:
            print("Hilo de actualizaciones terminado.")
            self.stop_edicion.set()

    def leer_datos_csv(self, hoja_id):
        mensaje = {"accion": "leer_datos_csv", "hoja_id": hoja_id, "usuario_id": self.sesion.usuario_id}
        respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)

        if respuesta["status"] == "ok":
            datos = respuesta["datos"]

            self.hoja_dict = {}

            if not datos or (len(datos) == 1 and not any(datos[0])):
                return {"status": "ok", "datos": datos}

            max_columnas = max(len(fila) for fila in datos)
            for i, fila in enumerate(datos):
                for j, valor in enumerate(fila):
                    celda = f"{chr(65 + j)}{i + 1}"
                    self.hoja_dict[celda] = valor

                if len(fila) < max_columnas:
                    fila.extend([''] * (max_columnas - len(fila)))

            return {"status": "ok", "datos": datos}
        else:
            print(respuesta["mensaje"])
            return {"status": "error", "mensaje": respuesta["mensaje"]}

    def imprimir_hoja_calculo(self):
        if not self.hoja_dict:
            return

        max_fila = max(int(celda[1:]) for celda in self.hoja_dict)
        max_columna = max(ord(celda[0]) for celda in self.hoja_dict) - 65

        datos = [[] for _ in range(max_fila)]
        for celda, valor in self.hoja_dict.items():
            col = ord(celda[0]) - 65
            fila = int(celda[1:]) - 1
            if len(datos[fila]) <= col:
                datos[fila].extend([''] * (col - len(datos[fila]) + 1))
            datos[fila][col] = valor

        max_columnas = max(len(fila) for fila in datos)
        for fila in datos:
            if len(fila) < max_columnas:
                fila.extend([''] * (max_columnas - len(fila)))

        columnas = [""] + [chr(65 + i) for i in range(max_columnas)]
        for i, fila in enumerate(datos):
            datos[i] = [str(i + 1)] + fila

        print("Contenido de la hoja de cálculo:")
        print(tabulate(datos, headers=columnas, tablefmt="github"))
