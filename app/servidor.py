import csv
import json
import os
import signal
import socket
import sqlite3
from hashlib import sha256
from queue import Queue
from threading import Thread, Lock

from config_util import cargar_configuracion
from utils import celda_a_indices


class Servidor:
    def __init__(self):
        self.host, self.port = cargar_configuracion()
        self.clientes = []
        self.hojas_de_calculo_dict = {}
        self.usuarios_hojas_compartidas = {}
        self.cola = Queue(maxsize=100)
        self.lock = Lock()
        self.socket_servidor = self.inicializar_socket()
        self.crear_directorio_hojas_de_calculo()
        self.escritor_thread = Thread(target=self.procesar_cola)
        self.escritor_thread.start()
        self.inicializar_base_datos()
        signal.signal(signal.SIGINT, self.manejar_sigint)

    def inicializar_socket(self):
        try:
            socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            socket_servidor.bind((self.host, self.port))
            return socket_servidor
        except Exception as e:
            print(f"Error al inicializar el socket: {e}")
            raise

    def crear_directorio_hojas_de_calculo(self):
        ruta_directorio = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hojas_de_calculo'))
        if not os.path.exists(ruta_directorio):
            os.makedirs(ruta_directorio)
            print(f"Directorio {ruta_directorio} creado.")

    def hoja_existe_en_base_de_datos(self, nombre_hoja, usuario):
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT COUNT(*) FROM hojas_calculo
                          JOIN permisos ON hojas_calculo.id = permisos.hoja_id
                          WHERE hojas_calculo.nombre = ? AND permisos.usuario_id = ?''', (nombre_hoja, usuario))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def inicializar_base_datos(self):
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                                id INTEGER PRIMARY KEY,
                                usuario TEXT UNIQUE,
                                pwd TEXT)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS hojas_calculo (
                                id INTEGER PRIMARY KEY,
                                nombre TEXT,
                                creador_id INTEGER,
                                FOREIGN KEY (creador_id) REFERENCES usuarios (id))''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS permisos (
                                id INTEGER PRIMARY KEY,
                                hoja_id INTEGER,
                                usuario_id INTEGER,
                                permisos TEXT,
                                FOREIGN KEY (hoja_id) REFERENCES hojas_calculo (id),
                                FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
                                UNIQUE(hoja_id, usuario_id))''')
            conn.commit()
            conn.close()
            print("Base de datos inicializada.")
        except Exception as e:
            print(f"Error al inicializar la base de datos: {e}")
            raise

    def crear_hoja_en_base_de_datos(self, nombre_hoja, usuario_id):
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO hojas_calculo (nombre, creador_id) VALUES (?, ?)', (nombre_hoja, usuario_id))
            hoja_id = cursor.lastrowid
            cursor.execute('INSERT INTO permisos (hoja_id, usuario_id, permisos) VALUES (?, ?, ?)',
                           (hoja_id, usuario_id, 'lectura-escritura'))
            conn.commit()
            conn.close()
            print(f"Hoja de cálculo '{nombre_hoja}' creada para el usuario ID '{usuario_id}' en la base de datos.")
        except sqlite3.Error as e:
            print(f"Error al crear la hoja de cálculo: {e}")
            raise

    def obtener_hojas_usuario(self, usuario_id):
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT hojas_calculo.nombre FROM hojas_calculo
                          JOIN permisos ON hojas_calculo.id = permisos.hoja_id
                          WHERE permisos.usuario_id = ?''', (usuario_id,))
        hojas = cursor.fetchall()
        conn.close()
        return [hoja[0] for hoja in hojas]

    def verificar_credenciales(self, usuario, pwd):
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        hashed_password = sha256(pwd.encode()).hexdigest()
        cursor.execute('SELECT id FROM usuarios WHERE usuario = ? AND pwd = ?', (usuario, hashed_password))
        resultado = cursor.fetchone()
        conn.close()
        return resultado[0] if resultado else None

    def procesar_cola(self):
        while True:
            nombre_hoja, celda, valor = self.cola.get()
            fila, columna = celda_a_indices(celda)
            self.hojas_de_calculo_dict.setdefault(nombre_hoja, {})[(fila, columna)] = valor
            self.guardar_en_csv(nombre_hoja)
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
            for user in self.usuarios_hojas_compartidas.values():
                if cliente_socket in user:
                    user.remove(cliente_socket)
            print(f"Conexión cerrada con {cliente_address}")

    def loop_cliente(self, cliente_socket):
        try:
            data = cliente_socket.recv(4096).decode()
            if not data:
                return

            mensaje = json.loads(data)
            usuario = mensaje.get("usuario")
            pwd = mensaje.get("pwd")

            if not usuario or not pwd:
                self.enviar_error(cliente_socket, "Credenciales inválidas")
                return

            usuario_id = self.verificar_credenciales(usuario, pwd)
            if not usuario_id:
                self.enviar_error(cliente_socket, "Credenciales inválidas")
                return

            hojas_usuario = self.obtener_hojas_usuario(usuario_id)
            cliente_socket.sendall(json.dumps({"status": "OK", "hojas": hojas_usuario}).encode())

            while True:
                data = cliente_socket.recv(4096).decode()
                if not data:
                    break

                try:
                    mensaje = json.loads(data)
                    opcion = mensaje.get("opcion", None)
                    nombre_hoja = mensaje.get("nombre_hoja", None)

                    if opcion:
                        if opcion == "nueva":
                            self.inicializar_hoja(nombre_hoja, usuario_id)
                            self.importar_csv_a_dict(nombre_hoja)
                            self.enviar_hoja_completa(cliente_socket, nombre_hoja)
                            self.asignar_permisos_cliente_dict(cliente_socket, nombre_hoja)  # Añadir esta línea
                        elif opcion == "existente":
                            if self.hoja_existe_en_base_de_datos(nombre_hoja, usuario_id):
                                self.importar_csv_a_dict(nombre_hoja)
                                self.enviar_hoja_completa(cliente_socket, nombre_hoja)
                                self.asignar_permisos_cliente_dict(cliente_socket, nombre_hoja)
                            else:
                                self.enviar_error(cliente_socket, "La hoja de cálculo no existe")
                        elif opcion == "compartir":
                            usuario_compartido = mensaje.get("usuario_compartido", None)
                            if usuario_compartido:
                                self.compartir_hoja(nombre_hoja, usuario_compartido, usuario_id, cliente_socket)
                            else:
                                self.enviar_error(cliente_socket, "Falta el usuario con quien compartir")
                        elif opcion == "registrar":
                            self.asignar_permisos_cliente_dict(cliente_socket, nombre_hoja)  # Manejo de la nueva opción
                        else:
                            self.enviar_error(cliente_socket, "Opción no válida")
                    else:
                        if 'nombre_hoja' in mensaje and 'celda' in mensaje and 'valor' in mensaje:
                            nombre_hoja = mensaje.get("nombre_hoja")
                            celda = mensaje.get("celda")
                            valor = mensaje.get("valor", "")
                            fila, columna = celda_a_indices(celda)
                            valor = f"{valor}({usuario})"
                            self.cola.put((nombre_hoja, celda, valor))
                        else:
                            self.enviar_error(cliente_socket, "Formato de mensaje incorrecto")
                except json.JSONDecodeError as e:
                    self.enviar_error(cliente_socket, f"Formato de mensaje JSON no válido: {e}")
                except ValueError as e:
                    self.enviar_error(cliente_socket, f"Valor inválido: {e}")
                except sqlite3.Error as e:
                    self.enviar_error(cliente_socket, f"Error en la base de datos: {e}")
                except Exception as e:
                    self.enviar_error(cliente_socket, f"Error desconocido: {e}")
        except Exception as e:
            self.enviar_error(cliente_socket, f"Error desconocido en la conexión: {e}")
            return

    def enviar_error(self, cliente_socket, mensaje_error):
        mensaje = json.dumps({"error": mensaje_error})
        try:
            cliente_socket.sendall(mensaje.encode())
        except Exception as e:
            print(f"Error enviando mensaje de error al cliente: {e}")

    def inicializar_hoja(self, nombre_hoja, usuario_id):
        if self.hoja_existe_en_base_de_datos(nombre_hoja, usuario_id):
            if nombre_hoja not in self.hojas_de_calculo_dict:
                self.hojas_de_calculo_dict[nombre_hoja] = {}
        else:
            try:
                self.crear_hoja_en_base_de_datos(nombre_hoja, usuario_id)
                self.hojas_de_calculo_dict[nombre_hoja] = {}
                self.guardar_en_csv(nombre_hoja)
            except Exception as e:
                raise ValueError(
                    f"No se pudo crear la hoja de cálculo '{nombre_hoja}' para el usuario ID '{usuario_id}': {e}")

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

    def asignar_permisos_cliente_dict(self, cliente_socket, nombre_hoja):
        if nombre_hoja not in self.usuarios_hojas_compartidas:
            self.usuarios_hojas_compartidas[nombre_hoja] = []
        if cliente_socket not in self.usuarios_hojas_compartidas[nombre_hoja]:
            self.usuarios_hojas_compartidas[nombre_hoja].append(cliente_socket)

    def notificar_clientes(self, nombre_hoja, celda, valor):
        if nombre_hoja in self.usuarios_hojas_compartidas:
            mensaje = json.dumps({"nombre_hoja": nombre_hoja, "celda": celda, "valor": valor})
            for cliente_socket in self.usuarios_hojas_compartidas[nombre_hoja]:
                try:
                    cliente_socket.sendall(mensaje.encode())
                except Exception as e:
                    print(f"Error notificando al cliente: {e}")

    def compartir_hoja(self, nombre_hoja, usuario_compartido, usuario_id, cliente_socket):
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario_compartido,))
        usuario_compartido_id = cursor.fetchone()
        if usuario_compartido_id:
            usuario_compartido_id = usuario_compartido_id[0]
            cursor.execute('SELECT id FROM hojas_calculo WHERE nombre = ? AND creador_id = ?',
                           (nombre_hoja, usuario_id))
            hoja_id = cursor.fetchone()
            if hoja_id:
                hoja_id = hoja_id[0]
                cursor.execute('INSERT OR IGNORE INTO permisos (hoja_id, usuario_id, permisos) VALUES (?, ?, ?)',
                               (hoja_id, usuario_compartido_id, 'lectura-escritura'))
                conn.commit()
                conn.close()
                cliente_socket.sendall(json.dumps({"status": "OK"}).encode())
            else:
                conn.close()
                self.enviar_error(cliente_socket,
                                  f"La hoja de cálculo '{nombre_hoja}' no existe o no tiene permisos para compartirla")
        else:
            conn.close()
            self.enviar_error(cliente_socket, f"El usuario {usuario_compartido} no existe")

    def iniciar_servidor(self):
        self.socket_servidor.listen(5)
        print("Servidor escuchando en", (self.host, self.port))
        while True:
            cliente_socket, cliente_address = self.socket_servidor.accept()
            cliente_thread = Thread(target=self.gestionar_cliente, args=(cliente_socket, cliente_address))
            cliente_thread.start()

    def manejar_sigint(self, signum, frame):
        print("\nTerminando el servidor...")
        self.socket_servidor.close()
        os._exit(0)


if __name__ == "__main__":
    servidor = Servidor()
    servidor.iniciar_servidor()
