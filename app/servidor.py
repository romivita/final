import csv
import json
import os
import socket
from queue import Queue
from threading import Thread, Lock


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
        self.hojas_de_calculo_dict = {}
        self.cola = Queue(maxsize=100)
        self.lock = Lock()

        self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_servidor.bind((self.host, self.port))

        self.escritor_thread = Thread(target=self.procesar_cola)
        self.escritor_thread.start()

    def inicializar_hoja(self, hoja_nombre):
        if hoja_nombre not in self.hojas_de_calculo_dict:
            self.hojas_de_calculo_dict[hoja_nombre] = {(1, 1): ""}

    def procesar_cola(self):
        while True:
            hoja_nombre, fila, columna, valor = self.cola.get()
            print(f'Cola get valor: {valor}')
            if hoja_nombre not in self.hojas_de_calculo_dict:
                self.hojas_de_calculo_dict[hoja_nombre] = {}
            self.hojas_de_calculo_dict[hoja_nombre][(fila, columna)] = valor
            self.guardar_en_csv(hoja_nombre)
            print(f'Cola task done valor: {valor}')
            self.notificar_clientes(hoja_nombre, fila, columna, valor)
            self.cola.task_done()

    def gestionar_cliente(self, cliente_socket, cliente_address):
        print(f"Conexión establecida con {cliente_address}")
        self.clientes.append((cliente_socket, cliente_address))

        cli_args = cliente_socket.recv(4096).decode()
        usuario, hoja_nombre = cli_args.split(",")
        print(f"Usuario conectado: {usuario}")
        print(f"Nombre de hoja de cálculo recibido: {hoja_nombre}")

        self.inicializar_hoja(hoja_nombre)
        self.importar_csv_a_dict(hoja_nombre)
        self.enviar_hoja_completa(cliente_socket, hoja_nombre)

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

    def importar_csv_a_dict(self, hoja_nombre):
        ruta_archivo = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{hoja_nombre}.csv"))
        if os.path.exists(ruta_archivo):
            file = open(ruta_archivo, "r", newline='')
            try:
                reader = csv.reader(file)
                for fila_idx, fila in enumerate(reader, start=1):
                    for col_idx, valor in enumerate(fila, start=1):
                        if valor:
                            if hoja_nombre not in self.hojas_de_calculo_dict:
                                self.hojas_de_calculo_dict[hoja_nombre] = {}
                            self.hojas_de_calculo_dict[hoja_nombre][(fila_idx, col_idx)] = valor
            finally:
                file.close()

    def guardar_en_csv(self, hoja_nombre):
        if hoja_nombre not in self.hojas_de_calculo_dict:
            return

        # Obtener las filas y columnas máximas para determinar el tamaño de la hoja de cálculo
        filas_max = max(fila for fila, _ in self.hojas_de_calculo_dict[hoja_nombre]) if self.hojas_de_calculo_dict[
            hoja_nombre] else 0
        columnas_max = max(columna for _, columna in self.hojas_de_calculo_dict[hoja_nombre]) if \
            self.hojas_de_calculo_dict[hoja_nombre] else 0

        # Escribir los datos de la hoja de cálculo en el archivo CSV
        ruta_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hojas_de_calculo', f"{hoja_nombre}.csv"))
        file = open(ruta_csv, "w", newline='')
        try:
            writer = csv.writer(file)
            for fila in range(1, filas_max + 1):
                fila_datos = [self.hojas_de_calculo_dict[hoja_nombre].get((fila, columna), "") for columna in
                              range(1, columnas_max + 1)]
                print(f"Escribiendo en CSV: {fila_datos}")
                writer.writerow(fila_datos)
        finally:
            file.close()

    def enviar_hoja_completa(self, cliente_socket, hoja_nombre):
        self.lock.acquire()
        try:
            hoja = self.hojas_de_calculo_dict.get(hoja_nombre, {})
            filas_max = max(fila for fila, _ in hoja) if hoja else 0
            columnas_max = max(columna for _, columna in hoja) if hoja else 0

            datos = []
            for fila in range(1, filas_max + 1):
                fila_datos = [hoja.get((fila, columna), "") for columna in range(1, columnas_max + 1)]
                datos.append(fila_datos)
        finally:
            self.lock.release()

        cliente_socket.sendall(json.dumps(datos).encode())

    def notificar_clientes(self, hoja_nombre, fila, columna, valor):
        mensaje = json.dumps({"hoja_nombre": hoja_nombre, "fila": fila, "columna": columna, "valor": valor})

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
