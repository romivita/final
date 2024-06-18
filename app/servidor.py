import csv
import json
import os
import socket
import time
from queue import Queue
from threading import Thread


class Servidor:
    def __init__(self):
        ruta_config = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fixtures/config.json'))
        file = open(ruta_config, "r")
        try:
            config = json.load(file)
            self.host = config["host"]
            self.port = config["port"]
        finally:
            file.close()

        self.clientes = []
        self.hojas_calculo = {}
        self.cola = Queue(maxsize=100)

        self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # To manipulate options at the sockets API level, level is specified as SOL_SOCKET
        # the SO_REUSEADDR flag tells the kernel to reuse a local socket in TIME_WAIT state, without waiting for its natural timeout to expire.
        self.socket_servidor.bind((self.host, self.port))

        self.escritor_thread = Thread(target=self.procesar_cola)
        self.escritor_thread.start()

    def procesar_cola(self):
        while True:
            hoja_nombre, fila, columna, valor = self.cola.get()
            print(f"{valor} procesando cola")
            if hoja_nombre not in self.hojas_calculo:
                self.hojas_calculo[hoja_nombre] = {}
            self.hojas_calculo[hoja_nombre][(fila, columna)] = valor
            self.guardar_en_csv(hoja_nombre)
            self.cola.task_done()

    def manejar_cliente(self, cliente_socket, cliente_address):
        print(f"Conexión establecida con {cliente_address}")
        self.clientes.append((cliente_socket, cliente_address))

        datos_iniciales = cliente_socket.recv(4096).decode()
        usuario, hoja_nombre = datos_iniciales.split(",")
        print(f"Usuario conectado: {usuario}")
        print(f"Nombre de hoja de cálculo recibido: {hoja_nombre}")

        self.cargar_csv(hoja_nombre)
        self.enviar_contenido_csv(cliente_socket, hoja_nombre)

        while True:
            data = cliente_socket.recv(4096).decode()
            if not data:
                break
            else:
                print(f"Datos recibidos: {data}")

            parts = data.split(",")
            if len(parts) != 4:
                print("Error: El formato de los datos no es válido.")
                continue

            usuario, fila, columna = parts[:3]
            fila, columna = map(int, [fila, columna])
            valor = f"{parts[3]}({usuario})"

            self.cola.put((hoja_nombre, fila, columna, valor))

        cliente_socket.close()
        self.clientes.remove((cliente_socket, cliente_address))
        print(f"Conexión cerrada con {cliente_address}")

    def enviar_contenido_csv(self, cliente_socket, hoja_nombre):
        ruta_archivo = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{hoja_nombre}.csv"))

        if os.path.exists(ruta_archivo):
            file = open(ruta_archivo, "r", newline='')
            try:
                reader = csv.reader(file)
                for fila in reader:
                    datos_fila = ','.join(fila)
                    cliente_socket.sendall(f"{datos_fila}\n".encode())
            finally:
                file.close()
        else:
            file = open(ruta_archivo, "w", newline='')
            try:
                cliente_socket.sendall("Se creó la hoja de cálculo\n".encode())
            finally:
                file.close()
        cliente_socket.shutdown(socket.SHUT_WR)

    def cargar_csv(self, hoja_nombre):
        ruta_archivo = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{hoja_nombre}.csv"))
        if os.path.exists(ruta_archivo):
            file = open(ruta_archivo, "r", newline='')
            try:
                reader = csv.reader(file)
                for fila_idx, fila in enumerate(reader, start=1):
                    for col_idx, valor in enumerate(fila, start=1):
                        if valor:
                            if hoja_nombre not in self.hojas_calculo:
                                self.hojas_calculo[hoja_nombre] = {}
                            self.hojas_calculo[hoja_nombre][(fila_idx, col_idx)] = valor
            finally:
                file.close()

    def guardar_en_csv(self, hoja_nombre):
        if hoja_nombre not in self.hojas_calculo:
            return

        # Obtener las filas y columnas máximas para determinar el tamaño de la hoja de cálculo
        filas_max = max(fila for fila, _ in self.hojas_calculo[hoja_nombre]) if self.hojas_calculo[hoja_nombre] else 0
        columnas_max = max(columna for _, columna in self.hojas_calculo[hoja_nombre]) if self.hojas_calculo[
            hoja_nombre] else 0

        # Escribir los datos de la hoja de cálculo en el archivo CSV
        ruta_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{hoja_nombre}.csv"))
        file = open(ruta_csv, "w", newline='')
        try:
            # TODO REMOVE Testing purpose
            time.sleep(10)
            writer = csv.writer(file)
            for fila in range(1, filas_max + 1):
                fila_datos = [self.hojas_calculo[hoja_nombre].get((fila, columna), "") for columna in
                              range(1, columnas_max + 1)]
                print(f"Escribiendo fila en CSV: {fila_datos}")
                writer.writerow(fila_datos)
        finally:
            file.close()

    def iniciar(self):
        self.socket_servidor.listen(5)
        print("Servidor escuchando en", (self.host, self.port))

        while True:
            cliente_socket, cliente_address = self.socket_servidor.accept()
            cliente_thread = Thread(target=self.manejar_cliente, args=(cliente_socket, cliente_address))
            cliente_thread.start()


if __name__ == "__main__":
    servidor = Servidor()
    servidor.iniciar()
