#!/opt/homebrew/bin/python3
import argparse
import logging

from config_util import cargar_configuracion
from hoja_calculo import HojaCalculo
from sesion import Sesion

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)


class Cliente:
    def __init__(self, usuario, host, port):
        self.sesion = Sesion(usuario, host, port)
        self.hoja_calculo = HojaCalculo(self.sesion)

    @staticmethod
    def mostrar_menu():
        print("\nOpciones:")
        print("1. Crear hoja de calculo")
        print("2. Editar una hoja de calculo")
        print("3. Compartir una hoja de calculo")
        print("4. Descargar hoja de calculo")
        print("5. Eliminar hoja de calculo")

    def seleccionar_opcion(self, opcion):
        opciones = {
            '1': self.hoja_calculo.crear_hoja,
            '2': self.hoja_calculo.seleccionar_hoja,
            '3': self.hoja_calculo.compartir_hoja,
            '4': self.hoja_calculo.descargar_hoja,
            '5': self.hoja_calculo.eliminar_hoja
        }

        accion = opciones.get(opcion)
        if accion:
            accion()
        else:
            print("Opcion no valida")

    def run(self):
        try:
            while True:
                self.hoja_calculo.listar_hojas()
                self.mostrar_menu()
                opcion = input("Selecciona una opcion: ")
                self.seleccionar_opcion(opcion)
        except KeyboardInterrupt:
            print("\nCerrando sesion")
        except ValueError as e:
            logging.error(f"Error de valor: {e}")
        except ConnectionError as e:
            logging.error(f"Error de conexion: {e}")
        except Exception as e:
            logging.error(f"Error inesperado: {e}")
        finally:
            self.sesion.desconectar()


if __name__ == "__main__":
    config_host, config_port = cargar_configuracion()

    parser = argparse.ArgumentParser(description="usuario de hojas de calculo")
    parser.add_argument('-u', '--user', required=True, help='usuario')
    parser.add_argument('--host', help='host del servidor', default=config_host)
    parser.add_argument('--port', type=int, help='puerto del servidor', default=config_port)

    args = parser.parse_args()
    usuario = args.user
    host = args.host
    port = args.port

    cliente = Cliente(usuario, host, port)
    cliente.run()
