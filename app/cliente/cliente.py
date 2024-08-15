import sys

from hoja_calculo import HojaCalculo
from sesion import Sesion


class Cliente:
    def __init__(self, usuario):
        self.sesion = Sesion(usuario)
        self.hoja_calculo = HojaCalculo(self.sesion)
        self.stop_event = self.sesion.stop_event

    def mostrar_menu(self):
        print("\nOpciones:")
        print("1. Crear hoja de calculo")
        print("2. Editar una hoja de calculo")
        print("3. Compartir una hoja de calculo")
        print("4. Descargar hoja de cálculo")

    def seleccionar_opcion(self, opcion):
        if opcion == '1':
            self.hoja_calculo.crear_hoja()
        elif opcion == '2':
            self.hoja_calculo.seleccionar_hoja()
        elif opcion == '3':
            self.hoja_calculo.compartir_hoja()
        elif opcion == "4":
            self.hoja_calculo.descargar_hoja()
        else:
            print("Opcion no valida.")

    def run(self):
        try:
            self.hoja_calculo.listar_hojas()
            while not self.stop_event.is_set():
                self.mostrar_menu()
                opcion = input("Selecciona una opcion: ")
                self.seleccionar_opcion(opcion)
        except KeyboardInterrupt:
            print("\nSaliendo del cliente...")
        finally:
            self.sesion.desconectar()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 cliente.py <usuario>")
        sys.exit(1)
    usuario = sys.argv[1]
    cliente = Cliente(usuario)
    cliente.run()
