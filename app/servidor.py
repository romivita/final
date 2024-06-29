import csv
import json
import os
import socket
from queue import Queue
from threading import Thread, Lock

from config_util import cargar_configuracion
from utils import celda_a_indices


class Servidor:
    def __init__(self):
        self.host, self.port = cargar_configuracion()
        self.clientes = []
        self.hojas_de_calculo_dict = {}
        self.cola = Queue(maxsize=100)
        self.lock = Lock()
        self.socket_servidor = self.inicializar_socket()
        self.escritor_thread = Thread(target=self.procesar_cola)
        self.escritor_thread.start()

    def inicializar_socket(self):
        socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_servidor.bind((self.host, self.port))
        return socket_servidor

    def inicializar_hoja(self, nombre_hoja):
        if nombre_hoja not in self.hojas_de_calculo_dict:
            self.hojas_de_calculo_dict[nombre_hoja] = {(1, 1): ""}

    def procesar_cola(self):
        while True:
            nombre_hoja, celda, valor = self.cola.get()
            fila, columna = celda_a_indices(celda)
            print(f'Cola get valor: {valor}')
            self.hojas_de_calculo_dict.setdefault(nombre_hoja, {})[(fila, columna)] = valor
            self.guardar_en_csv(nombre_hoja)
            print(f'Cola task done valor: {valor}')
            self.notificar_clientes(nombre_hoja, celda, valor)
            self.cola.task_done()

    def gestionar_cliente(self, cliente_socket, cliente_address):
        print(f"Conexión establecida con {cliente_address}")
        self.clientes.append((cliente_socket, cliente_address))
        try:
            self.loop_cliente(cliente_socket)
        finally:
            cliente_socket.close()
            self.clientes.remove((cliente_socket, cliente_address))
            print(f"Conexión cerrada con {cliente_address}")

    def loop_cliente(self, cliente_socket):
        cli_args = cliente_socket.recv(4096).decode()
        usuario, nombre_hoja = cli_args.split(",")
        print(f"Usuario conectado: {usuario}")
        print(f"Nombre de hoja de cálculo recibido: {nombre_hoja}")

        self.inicializar_hoja(nombre_hoja)
        self.importar_csv_a_dict(nombre_hoja)
        self.enviar_hoja_completa(cliente_socket, nombre_hoja)

        while True:
            data = cliente_socket.recv(4096).decode()
            if not data:
                break
            print(f"Datos recibidos: {data}")

            try:
                mensaje = json.loads(data)
                usuario = mensaje.get("usuario")
                celda = mensaje.get("celda")
                valor = mensaje.get("valor", "")

                if not (usuario and celda):
                    raise ValueError("Datos incompletos en el mensaje")

                valor = f"{valor}({usuario})"
                self.cola.put((nombre_hoja, celda, valor))

            except json.JSONDecodeError as e:
                print(f"Error en el formato de los datos: {e}")
                self.enviar_error(cliente_socket, "Formato de datos no válido")
            except ValueError as e:
                print(f"Error en el contenido de los datos: {e}")
                self.enviar_error(cliente_socket, str(e))
            except Exception as e:
                print(f"Error desconocido: {e}")
                self.enviar_error(cliente_socket, "Error desconocido")

    def enviar_error(self, cliente_socket, mensaje_error):
        mensaje = json.dumps({"error": mensaje_error})
        try:
            cliente_socket.sendall(mensaje.encode())
        except Exception as e:
            print(f"Error enviando mensaje de error al cliente: {e}")

    def importar_csv_a_dict(self, nombre_hoja):
        ruta_archivo = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{nombre_hoja}.csv"))
        if os.path.exists(ruta_archivo):
            file = open(ruta_archivo, "r", newline='')
            try:
                reader = csv.reader(file)
                for fila_idx, fila in enumerate(reader, start=1):
                    for col_idx, valor in enumerate(fila, start=1):
                        if valor:
                            self.hojas_de_calculo_dict.setdefault(nombre_hoja, {})[(fila_idx, col_idx)] = valor
            finally:
                file.close()

    def guardar_en_csv(self, nombre_hoja):
        if nombre_hoja not in self.hojas_de_calculo_dict:
            return

        filas_max = max(fila for fila, _ in self.hojas_de_calculo_dict[nombre_hoja]) if self.hojas_de_calculo_dict[
            nombre_hoja] else 0
        columnas_max = max(columna for _, columna in self.hojas_de_calculo_dict[nombre_hoja]) if \
            self.hojas_de_calculo_dict[nombre_hoja] else 0

        ruta_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{nombre_hoja}.csv"))
        file = open(ruta_csv, "w", newline='')
        try:
            writer = csv.writer(file)
            for fila in range(1, filas_max + 1):
                fila_datos = [self.hojas_de_calculo_dict[nombre_hoja].get((fila, columna), "") for columna in
                              range(1, columnas_max + 1)]
                print(f"Escribiendo en CSV: {fila_datos}")
                writer.writerow(fila_datos)
        finally:
            file.close()

    def enviar_hoja_completa(self, cliente_socket, nombre_hoja):
        self.lock.acquire()
        try:
            hoja = self.hojas_de_calculo_dict.get(nombre_hoja, {})
            filas_max = max(fila for fila, _ in hoja) if hoja else 0
            columnas_max = max(columna for _, columna in hoja) if hoja else 0

            datos = []
            for fila in range(1, filas_max + 1):
                fila_datos = [hoja.get((fila, columna), "") for columna in range(1, columnas_max + 1)]
                datos.append(fila_datos)
        finally:
            self.lock.release()

        cliente_socket.sendall(json.dumps(datos).encode())

    def notificar_clientes(self, nombre_hoja, celda, valor):
        mensaje = json.dumps({"nombre_hoja": nombre_hoja, "celda": celda, "valor": valor})
        for cliente_socket, _ in self.clientes:
            try:
                cliente_socket.sendall(mensaje.encode())
            except Exception as e:
                print(f"Error notificando al cliente: {e}")

    def iniciar(self):
        self.socket_servidor.listen(5)
        print("Servidor escuchando en", (self.host, self.port))
        while True:
            cliente_socket, cliente_address = self.socket_servidor.accept()
            cliente_thread = Thread(target=self.gestionar_cliente, args=(cliente_socket, cliente_address))
            cliente_thread.start()


if __name__ == "__main__":
    servidor = Servidor()
    servidor.iniciar()
