#!/opt/homebrew/bin/python3
import argparse

from config_util import cargar_configuracion
from hoja_calculo import HojaCalculo
from sesion import Sesion


class Cliente:
    def __init__(self, usuario, host, port):
        self.sesion = Sesion(usuario, host, port)
        self.hoja_calculo = HojaCalculo(self.sesion)
        self.stop_event = self.sesion.stop_event

    def mostrar_menu(self):
        print("\nOpciones:")
        print("1. Crear hoja de calculo")
        print("2. Editar una hoja de calculo")
        print("3. Compartir una hoja de calculo")
        print("4. Descargar hoja de calculo")
        print("5. Eliminar hoja de calculo")

    def seleccionar_opcion(self, opcion):
        if opcion == '1':
            self.hoja_calculo.crear_hoja()
        elif opcion == '2':
            self.hoja_calculo.seleccionar_hoja()
        elif opcion == '3':
            self.hoja_calculo.compartir_hoja()
        elif opcion == "4":
            self.hoja_calculo.descargar_hoja()
        elif opcion == "5":
            self.hoja_calculo.eliminar_hoja()
        else:
            print("Opcion no valida")

    def run(self):
        try:
            while not self.stop_event.is_set():
                self.hoja_calculo.listar_hojas()
                self.mostrar_menu()
                opcion = input("Selecciona una opcion: ")
                self.seleccionar_opcion(opcion)
        except KeyboardInterrupt:
            print("\nSaliendo del cliente por interrupcion...")
        except Exception as e:
            print(f"Error inesperado: {e}")
        finally:
            self.sesion.desconectar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="usuario de hojas de calculo")
    parser.add_argument('-u', '--user', required=True, help='usuario')
    parser.add_argument('--host', help='host del servidor')
    parser.add_argument('--port', type=int, help='puerto del servidor')

    args = parser.parse_args()
    usuario = args.user
    host = args.host
    port = args.port

    if not host or not port:
        config_host, config_port = cargar_configuracion()

        if not host:
            host = config_host
        if not port:
            port = config_port

    cliente = Cliente(usuario, host, port)
    cliente.run()
