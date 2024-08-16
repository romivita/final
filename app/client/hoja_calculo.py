import csv
import os
import re
import select
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

    def listar_hojas(self):
        mensaje = {"accion": "listar_hojas", "creador_id": self.sesion.usuario_id}
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
        mensaje = {"accion": "crear_hoja", "nombre": nombre, "creador_id": self.sesion.usuario_id}
        respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)
        if respuesta["status"] == "ok":
            self.editar_hoja(respuesta["hoja_id"])
        else:
            print(respuesta["mensaje"])

    def seleccionar_hoja(self):
        if not self.hojas:
            print("No tienes hojas de cálculo disponibles para editar.")
            return

        indice = int(input("Selecciona el número de hoja: ")) - 1
        if 0 <= indice < len(self.hojas):
            hoja_seleccionada = self.hojas[indice]
            hoja_id = self.obtener_hoja_id(hoja_seleccionada[1])
            if hoja_id:
                self.editar_o_ver_hoja(hoja_id)
        else:
            print("Selección no válida.")

    def editar_o_ver_hoja(self, hoja_id):
        permisos_respuesta = self.obtener_permisos(hoja_id)
        if permisos_respuesta["status"] == "ok":
            permisos = permisos_respuesta.get("permisos")
            if permisos == "lectura y escritura":
                self.editar_hoja(hoja_id)
            elif permisos == "solo lectura":
                respuesta = self.leer_datos_csv(hoja_id)
                if respuesta["status"] == "ok":
                    self.imprimir_hoja_calculo()
                else:
                    print(respuesta["mensaje"])
            else:
                print("No tienes permisos suficientes para editar esta hoja.")
        else:
            print(permisos_respuesta["mensaje"])

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

    def obtener_hoja_id(self, nombre):
        mensaje = {"accion": "obtener_hoja_id", "nombre": nombre, "usuario_id": self.sesion.usuario_id}
        respuesta = Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)
        if respuesta["status"] == "ok":
            return respuesta["hoja_id"]
        else:
            print(respuesta["mensaje"])
            return None

    def obtener_permisos(self, hoja_id):
        mensaje = {"accion": "obtener_permisos", "hoja_id": hoja_id, "usuario_id": self.sesion.usuario_id}
        return Comunicacion.enviar_y_recibir(mensaje, self.sesion.sock)

    def editar_hoja(self, hoja_id):
        self.hoja_editada = hoja_id
        self.hoja_dict = {}
        respuesta = self.leer_datos_csv(hoja_id)
        if respuesta["status"] == "ok":
            self.imprimir_hoja_calculo()

        self.update_lock = threading.Lock()

        hilo_actualizaciones = threading.Thread(target=self.manejar_actualizaciones, daemon=True)
        hilo_actualizaciones.start()
        try:
            while True:
                try:
                    celda = input("Celda: ").strip().upper()
                    if not re.match(r'^[a-zA-Z]+\d+$', celda):
                        print("Formato de celda no valido. Intenta de nuevo.")
                        continue
                    valor = input("Valor: ").strip()
                    valor_evaluado = evaluar_expresion(valor)
                    mensaje = {"accion": "editar_hoja", "hoja_id": hoja_id, "celda": celda, "valor": valor_evaluado,
                               "usuario_id": self.sesion.usuario_id}
                    Comunicacion.enviar_mensaje(mensaje, self.sesion.sock)
                except KeyboardInterrupt:
                    print("\nEdicion de hoja finalizada.")
                    break
                except Exception as e:
                    print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nEdicion de hoja finalizada. Desconectando...")
        finally:
            self.sesion.stop_event.set()
            hilo_actualizaciones.join()

    def manejar_actualizaciones(self):
        while not self.sesion.stop_event.is_set():
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
                                f"\nActualizacion recibida en hoja {hoja_id}: Celda {celda} = {valor} (Usuario ID: {usuario_id})")
                            self.update_lock.acquire()
                            try:
                                self.hoja_dict[celda] = valor
                                self.imprimir_hoja_calculo()
                            finally:
                                self.update_lock.release()
            except Exception as e:
                if self.sesion.stop_event.is_set():
                    break

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
