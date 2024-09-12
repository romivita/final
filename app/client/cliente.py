#!/opt/homebrew/bin/python3
import sys

from hoja_calculo import HojaCalculo
from sesion import Sesion


class Cliente:
    def __init__(self, usuario, host):
        self.sesion = Sesion(usuario, host)
        self.hoja_calculo = HojaCalculo(self.sesion)
        self.stop_event = self.sesion.stop_event

    def mostrar_menu(self):
        print("\nOpciones:")
        print("1. Crear hoja de calculo")
        print("2. Editar una hoja de calculo")
        print("3. Compartir una hoja de calculo")
        print("4. Descargar hoja de cálculo")
        print("5. Eliminar hoja de cálculo")

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
            print("Opcion no valida.")

    def run(self):
        try:
            while not self.stop_event.is_set():
                self.hoja_calculo.listar_hojas()
                self.mostrar_menu()
                opcion = input("Selecciona una opción: ")
                self.seleccionar_opcion(opcion)
        except KeyboardInterrupt:
            print("\nSaliendo del cliente por interrupción...")
        except Exception as e:
            print(f"Ha ocurrido un error inesperado: {e}")
        finally:
            self.sesion.desconectar()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 cliente.py <usuario> <host>")
        sys.exit(1)
    usuario = sys.argv[1]
    host = sys.argv[2]
    cliente = Cliente(usuario, host)
    cliente.run()
