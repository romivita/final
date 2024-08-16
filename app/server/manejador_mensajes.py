from autenticacion import Autenticacion
from gestor_hojas import GestorHojas


class ManejadorMensajes:
    @staticmethod
    def procesar_mensaje(mensaje, conn, servidor):
        if mensaje['accion'] == 'iniciar_sesion':
            return Autenticacion.iniciar_sesion(mensaje, servidor, conn)
        elif mensaje['accion'] == 'crear_hoja':
            return GestorHojas.crear_hoja(mensaje, servidor, conn)
        elif mensaje['accion'] == 'listar_hojas':
            return GestorHojas.listar_hojas(mensaje['creador_id'])
        elif mensaje['accion'] == 'obtener_hoja_id':
            return GestorHojas.obtener_hoja_id(mensaje)
        elif mensaje['accion'] == 'editar_hoja':
            return GestorHojas.editar_hoja(mensaje, servidor, conn)
        elif mensaje['accion'] == 'compartir_hoja':
            return GestorHojas.compartir_hoja(mensaje)
        elif mensaje['accion'] == 'obtener_permisos':
            return GestorHojas.obtener_permisos(mensaje)
        elif mensaje['accion'] == 'leer_datos_csv':
            return GestorHojas.leer_datos_csv(mensaje['hoja_id'], servidor, conn)
        elif mensaje['accion'] == 'descargar_hoja':
            return GestorHojas.descargar_hoja(mensaje['hoja_id'])
        elif mensaje['accion'] == 'desconectar':
            return {"status": "ok", "mensaje": "Desconectado"}
        return {"status": "error", "mensaje": "Accion no valida"}
