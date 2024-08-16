import os
import queue
import signal
import socket
import sys
import threading

from comunicacion import Comunicacion
from config_util import cargar_configuracion
from gestor_hojas import GestorHojas
from manejador_mensajes import ManejadorMensajes


class Servidor:
    def __init__(self):
        self.host, self.port = cargar_configuracion()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.hojas_clientes = {}
        self.cola_ediciones = queue.Queue()
        self.lock = threading.Lock()

        self.directorio_archivos = os.path.join(os.path.dirname(__file__), '..', 'hojas_de_calculo')
        if not os.path.exists(self.directorio_archivos):
            os.makedirs(self.directorio_archivos)

        signal.signal(signal.SIGINT, self.terminar_servidor)

        hilo_procesar_cola = threading.Thread(target=self.procesar_cola_ediciones, daemon=True)
        hilo_procesar_cola.start()

        print(f"Servidor iniciado en {self.host}:{self.port}")

    def procesar_cola_ediciones(self):
        while True:
            hoja_id, celda, valor, usuario_id = self.cola_ediciones.get()
            resultado = GestorHojas.aplicar_edicion(hoja_id, celda, valor)
            if resultado["status"] == "ok":
                GestorHojas.notificar_actualizacion(hoja_id, celda, valor, usuario_id, self)
            self.cola_ediciones.task_done()

    def manejar_cliente(self, conn, addr):
        print(f"Conexion desde {addr}")

        try:
            while True:
                mensaje = Comunicacion.recibir_mensaje(conn)
                if not mensaje:
                    break
                respuesta = ManejadorMensajes.procesar_mensaje(mensaje, conn, self)
                Comunicacion.enviar_mensaje(respuesta, conn)

                if mensaje['accion'] == 'desconectar':
                    break
        finally:
            conn.close()
            self.eliminar_conexion(conn)

    def eliminar_conexion(self, conn):
        self.lock.acquire()
        try:
            for hoja_id in list(self.hojas_clientes.keys()):
                if conn in self.hojas_clientes[hoja_id]:
                    self.hojas_clientes[hoja_id].remove(conn)
                    if not self.hojas_clientes[hoja_id]:
                        del self.hojas_clientes[hoja_id]
        finally:
            self.lock.release()

    def iniciar(self):
        print("Servidor iniciado, esperando conexiones...")
        while True:
            conn, addr = self.sock.accept()
            hilo_cliente = threading.Thread(target=self.manejar_cliente, args=(conn, addr))
            hilo_cliente.start()

    def terminar_servidor(self, sig, frame):
        print("Terminando servidor...")
        self.sock.close()
        sys.exit(0)
