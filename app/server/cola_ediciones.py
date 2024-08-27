import csv
import logging
import os
import queue
import threading

from comunicacion import Comunicacion
from utils import celda_a_indices


class ColaDeEdiciones:
    def __init__(self, servidor):
        self.servidor = servidor
        self.cola = queue.Queue()
        self.directorio_archivos = servidor.directorio_archivos
        self.edit_lock = threading.Lock()
        self.stop_event = threading.Event()

        threading.Thread(target=self.procesar_cola_ediciones, daemon=True).start()

    def agregar_edicion(self, mensaje):
        hoja_id = mensaje['hoja_id']
        celda = mensaje['celda']
        valor = mensaje['valor']
        usuario_id = mensaje['usuario_id']
        self.cola.put((hoja_id, celda, valor, usuario_id))

    def procesar_cola_ediciones(self):
        while self.servidor.activo:
            try:
                hoja_id, celda, valor, usuario_id = self.cola.get()
                resultado = self.aplicar_edicion(hoja_id, celda, valor)
                if resultado["status"] == "ok":
                    self.notificar_actualizacion(hoja_id, celda, valor, usuario_id)
                self.cola.task_done()
            except queue.Empty:
                continue

    def aplicar_edicion(self, hoja_id, celda, valor):
        archivo_csv = os.path.join(self.directorio_archivos, f'{hoja_id}.csv')
        if not os.path.exists(archivo_csv):
            return {"status": "error", "mensaje": "Hoja no encontrada"}

        fila, columna = celda_a_indices(celda)
        self.actualizar_celda(archivo_csv, fila, columna, valor)
        return {"status": "ok", "mensaje": "Edición aplicada"}

    def actualizar_celda(self, archivo_csv, fila, columna, valor):
        with open(archivo_csv, 'r', newline='') as archivo:
            contenido = list(csv.reader(archivo))

        while len(contenido) <= fila:
            contenido.append([])

        while len(contenido[fila]) <= columna:
            contenido[fila].append('')

        contenido[fila][columna] = valor

        with open(archivo_csv, 'w', newline='') as archivo:
            csv.writer(archivo).writerows(contenido)

    def notificar_actualizacion(self, hoja_id, celda, valor, usuario_id):
        with self.edit_lock:
            conexiones = self.servidor.clientes_hojas.get(hoja_id, [])
            mensaje = {"accion": "actualizar_celda", "hoja_id": hoja_id, "celda": celda, "valor": valor,
                       "usuario_id": usuario_id}
            for conn in conexiones:
                try:
                    Comunicacion.enviar_mensaje(mensaje, conn)
                except Exception as e:
                    logging.error(f"Error notificando a un cliente: {e}")
