import logging
import os
import signal
import socket
import threading

from autenticacion import Autenticacion
from cola_ediciones import ColaDeEdiciones
from comunicacion import Comunicacion
from gestor_hojas import GestorDeHojas

ACCIONES = {
    "iniciar_sesion": "iniciar_sesion",
    "crear_hoja": "crear_hoja",
    "listar_hojas": "listar_hojas",
    "obtener_hoja_id": "obtener_hoja_id",
    "obtener_permisos": "obtener_permisos",
    "leer_datos_csv": "leer_datos_csv",
    "editar_celda": "editar_celda",
    "compartir_hoja": "compartir_hoja",
    "descargar_hoja": "descargar_hoja",
    "eliminar_hoja": "eliminar_hoja",
    "desconectar": "desconectar"
}


class Servidor:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock_v4 = None
        self.sock_v6 = None
        self.clientes_hojas = {}
        self.lock = threading.Lock()
        self.activo = threading.Event()
        self.activo.set()

        self.directorio_archivos = os.path.join(os.path.dirname(__file__), '..', 'hojas_de_calculo')
        os.makedirs(self.directorio_archivos, exist_ok=True)

        self.gestor_sesiones = Autenticacion(self)
        self.gestor_hojas = GestorDeHojas(self)
        self.cola_ediciones = ColaDeEdiciones(self)

        signal.signal(signal.SIGINT, self.terminar_servidor)

        logging.info(f"Servidor iniciado en {self.host}:{self.port}")

    def configurar_socket(self, familia):
        sock = socket.socket(familia, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(5)
        return sock

    def iniciar(self):
        direcciones = socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        hilos = []

        for direccion in direcciones:
            familia = direccion[0]
            if familia == socket.AF_INET and not self.sock_v4:
                self.sock_v4 = self.configurar_socket(socket.AF_INET)
                hilos.append(threading.Thread(target=self.escuchar_conexiones, args=(self.sock_v4,)))
            elif familia == socket.AF_INET6 and not self.sock_v6:
                self.sock_v6 = self.configurar_socket(socket.AF_INET6)
                hilos.append(threading.Thread(target=self.escuchar_conexiones, args=(self.sock_v6,)))

        for hilo in hilos:
            hilo.start()

        for hilo in hilos:
            hilo.join()

    def escuchar_conexiones(self, sock):
        logging.info(f"Servidor escuchando en {sock.getsockname()}")
        while self.activo.is_set():
            try:
                sock.settimeout(1.0)
                conn, addr = sock.accept()
                threading.Thread(target=self.manejar_cliente, args=(conn, addr)).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def manejar_cliente(self, conn, addr):
        logging.info(f"Conexion desde {addr}")
        try:
            while self.activo.is_set():
                mensaje = Comunicacion.recibir_mensaje(conn)
                if not mensaje:
                    break
                respuesta = self.procesar_mensaje(mensaje, conn)
                Comunicacion.enviar_mensaje(respuesta, conn)
                if mensaje.get('accion') == ACCIONES["desconectar"]:
                    logging.info(f"Desconectar cliente {addr}")
                    break
        except (ConnectionResetError, ConnectionAbortedError):
            logging.warning(f"Conexion interrumpida desde {addr}")
        except Exception as e:
            logging.error(f"Error manejando cliente {addr}: {e}")
        finally:
            conn.close()
            self.eliminar_conexion(conn)
            logging.info(f"Conexion cerrada desde {addr}")

    def eliminar_conexion(self, conn):
        with self.lock:
            hojas_a_eliminar = [hoja_id for hoja_id, conexiones in self.clientes_hojas.items() if conn in conexiones]
            for hoja_id in hojas_a_eliminar:
                self.clientes_hojas[hoja_id].remove(conn)
                if not self.clientes_hojas[hoja_id]:
                    del self.clientes_hojas[hoja_id]

    def terminar_servidor(self, sig=None, frame=None):
        self.activo.clear()

        self.cerrar_socket(self.sock_v4)
        self.cerrar_socket(self.sock_v6)
        self.cola_ediciones.detener_ediciones()

        logging.info("Servidor detenido.")

    def cerrar_socket(self, sock):
        if sock:
            sock.close()

    def asociar_cliente_hoja(self, conn, hoja_id):
        with self.lock:
            if hoja_id not in self.clientes_hojas:
                self.clientes_hojas[hoja_id] = []
            if conn not in self.clientes_hojas[hoja_id]:
                self.clientes_hojas[hoja_id].append(conn)

    def asociar_cliente_hojas(self, conn, hojas_ids):
        with self.lock:
            for hoja_id in hojas_ids:
                self.asociar_cliente_hoja(conn, hoja_id)

    def procesar_mensaje(self, mensaje, conn):
        accion = mensaje.get("accion")
        if accion in ACCIONES:
            if accion == ACCIONES["iniciar_sesion"]:
                return self.gestor_sesiones.iniciar_sesion(mensaje, conn)
            elif accion == ACCIONES["crear_hoja"]:
                return self.gestor_hojas.crear_hoja(mensaje)
            elif accion == ACCIONES["listar_hojas"]:
                return self.gestor_hojas.listar_hojas(mensaje, conn)
            elif accion == ACCIONES["obtener_hoja_id"]:
                return self.gestor_hojas.obtener_hoja_id(mensaje)
            elif accion == ACCIONES["obtener_permisos"]:
                return self.gestor_hojas.obtener_permisos_usuario(mensaje)
            elif accion == ACCIONES["leer_datos_csv"]:
                return self.gestor_hojas.leer_datos_csv(mensaje, conn)
            elif accion == ACCIONES["editar_celda"]:
                return self.gestor_hojas.editar_celda(mensaje, conn)
            elif accion == ACCIONES["compartir_hoja"]:
                return self.gestor_hojas.compartir_hoja(mensaje)
            elif accion == ACCIONES["descargar_hoja"]:
                return self.gestor_hojas.descargar_hoja(mensaje)
            elif accion == ACCIONES["eliminar_hoja"]:
                return self.gestor_hojas.eliminar_hoja(mensaje)
            elif accion == ACCIONES["desconectar"]:
                return {"status": "ok", "mensaje": "Desconectado"}
        return {"status": "error", "mensaje": "Accion desconocida"}
