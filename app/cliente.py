import getpass
import re
import socket
import sys
import threading

from tabulate import tabulate

from comunicacion import Comunicacion
from config_util import cargar_configuracion
from utils import evaluar_expresion


class Cliente:
    def __init__(self, usuario):
        self.usuario = usuario
        self.host, self.port = cargar_configuracion()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.sock.connect((self.host, self.port))
        except ConnectionRefusedError:
            sys.exit(
                f"No se pudo conectar al servidor en {self.host}:{self.port}."
                f"\nAsegurate de que el servidor este corriendo e intentalo nuevamente.")

        self.usuario_id = self.autenticar_usuario()
        self.hojas = []
        self.hoja_editada = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

    def autenticar_usuario(self):
        pwd = getpass.getpass("Contraseña: ")
        mensaje = {"accion": "iniciar_sesion", "usuario": self.usuario, "pwd": pwd}
        Comunicacion.enviar(mensaje, self.sock)
        respuesta = Comunicacion.recibir(self.sock)
        print(respuesta["mensaje"])
        if respuesta["status"] == "ok":
            return respuesta["usuario_id"]
        else:
            sys.exit("Error de autenticacion. Saliendo...")

    def crear_hoja(self, nombre):
        mensaje = {"accion": "crear_hoja", "nombre": nombre, "creador_id": self.usuario_id}
        Comunicacion.enviar(mensaje, self.sock)
        respuesta = Comunicacion.recibir(self.sock)
        if respuesta["status"] == "ok":
            return respuesta["hoja_id"]
        else:
            print(respuesta["mensaje"])
            return None

    def listar_hojas(self):
        mensaje = {"accion": "listar_hojas", "creador_id": self.usuario_id}
        Comunicacion.enviar(mensaje, self.sock)
        respuesta = Comunicacion.recibir(self.sock)
        if respuesta['status'] == 'ok':
            hojas = respuesta['hojas_creadas'] + respuesta['hojas_lectura_escritura'] + respuesta['hojas_lectura']
            self.hojas = hojas
            if hojas:
                headers = ["#", "Nombre", "Creador"]
                tabla_hojas = [[i + 1, hoja[1], hoja[-1]] for i, hoja in enumerate(hojas)]
                print(tabulate(tabla_hojas, headers, tablefmt="github"))
            else:
                print("No tienes hojas de calculo.")
        else:
            print(respuesta["mensaje"])

    def obtener_hoja_id(self, nombre_hoja):
        mensaje = {"accion": "obtener_hoja_id", "nombre": nombre_hoja, "usuario_id": self.usuario_id}
        Comunicacion.enviar(mensaje, self.sock)
        respuesta = Comunicacion.recibir(self.sock)
        if respuesta["status"] == "ok":
            return respuesta["hoja_id"]
        else:
            print(respuesta["mensaje"])
            return None

    def editar_hoja(self, hoja_id):
        self.hoja_editada = hoja_id
        hilo_actualizaciones = threading.Thread(target=self.manejar_actualizaciones, daemon=True)
        hilo_actualizaciones.start()
        try:
            while True:
                try:
                    celda = input("Celda: ").strip().upper()
                    if not re.match(r'^[a-zA-Z]+\d+$', celda):
                        print("Formato de celda no valido. Intenta de nuevo.")
                        continue
                    valor = input("Valor: ").strip()
                    valor_evaluado = evaluar_expresion(valor)
                    mensaje = {"accion": "editar_hoja", "hoja_id": hoja_id, "celda": celda, "valor": valor_evaluado,
                               "usuario_id": self.usuario_id}
                    Comunicacion.enviar(mensaje, self.sock)
                except KeyboardInterrupt:
                    print("\nEdicion de hoja finalizada.")
                    break
                except Exception as e:
                    print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nEdicion de hoja finalizada. Desconectando...")
        finally:
            self.stop_event.set()
            hilo_actualizaciones.join()
            self.desconectar()

    def compartir_hoja(self):
        hojas_creadas = [hoja for hoja in self.hojas if hoja[2] == self.usuario_id]
        if not hojas_creadas:
            print("No tienes hojas de calculo propias para compartir.")
            return
        print("Selecciona la hoja de calculo que deseas compartir:")
        for i, hoja in enumerate(hojas_creadas):
            print(f"{i + 1}. {hoja[1]}")
        opcion_hoja = int(input("Selecciona una hoja: ")) - 1
        if opcion_hoja < 0 or opcion_hoja >= len(hojas_creadas):
            print("Opcion no valida.")
            return
        hoja_id = hojas_creadas[opcion_hoja][0]
        nombre_usuario = input("Nombre del usuario con quien compartir: ")
        print("Selecciona el permiso que deseas otorgar:")
        print("1. Solo lectura")
        print("2. Lectura y escritura")
        opcion_permiso = input("Selecciona una opcion: ")
        permisos = "lectura y escritura" if opcion_permiso == '2' else "solo lectura"
        mensaje = {"accion": "compartir_hoja", "hoja_id": hoja_id, "nombre_usuario": nombre_usuario,
                   "permisos": permisos}
        Comunicacion.enviar(mensaje, self.sock)
        respuesta = Comunicacion.recibir(self.sock)
        print(respuesta["mensaje"])

    def ver_hoja(self, hoja_id):
        mensaje = {"accion": "ver_hoja", "hoja_id": hoja_id, "usuario_id": self.usuario_id}
        Comunicacion.enviar(mensaje, self.sock)
        respuesta = Comunicacion.recibir(self.sock)
        if respuesta["status"] == "ok":
            datos = respuesta["datos"]
            if datos:
                num_filas = len(datos)
                num_columnas = len(datos[0]) if num_filas > 0 else 0
                columnas = [""] + [chr(65 + i) for i in range(num_columnas)]
                for i, fila in enumerate(datos):
                    datos[i] = [str(i + 1)] + fila
                print("Contenido de la hoja de calculo:")
                print(tabulate(datos, headers=columnas, tablefmt="github"))
            else:
                print("La hoja de calculo esta vacia.")
            return respuesta.get("permisos", "solo lectura")
        else:
            print(respuesta["mensaje"])
            return "solo lectura"

    def manejar_actualizaciones(self):
        while not self.stop_event.is_set():
            try:
                respuesta = Comunicacion.recibir(self.sock)
                if respuesta and respuesta.get("accion") == "actualizacion":
                    hoja_id = respuesta.get("hoja_id")
                    celda = respuesta.get("celda")
                    valor = respuesta.get("valor")
                    usuario_id = respuesta.get("usuario_id")
                    if hoja_id == self.hoja_editada:
                        print(
                            f"\nActualizacion recibida en hoja {hoja_id}: Celda {celda} = {valor} (Usuario ID: {usuario_id})")
            except Exception as e:
                if self.stop_event.is_set():
                    break
                print(f"Error en actualizaciones: {e}")

    def desconectar(self):
        try:
            mensaje = {"accion": "desconectar"}
            Comunicacion.enviar(mensaje, self.sock)
        except Exception as e:
            print(f"Error al enviar mensaje de desconexion: {e}")
        finally:
            self.sock.close()

    def run(self):
        try:
            self.listar_hojas()
            while True:
                print("\nOpciones:")
                print("1. Crear hoja de calculo")
                print("2. Seleccionar una hoja de calculo")
                print("3. Compartir una hoja de calculo")
                opcion = input("Selecciona una opcion: ")
                if opcion == '1':
                    nombre = input("Nombre de la hoja de calculo: ")
                    hoja_id = self.crear_hoja(nombre)
                    if hoja_id:
                        self.editar_hoja(hoja_id)
                elif opcion == '2':
                    if not self.hojas:
                        print("No tienes hojas de calculo disponibles para editar.")
                    else:
                        indice = int(input("Selecciona el numero de hoja: ")) - 1
                        if 0 <= indice < len(self.hojas):
                            hoja_seleccionada = self.hojas[indice]
                            hoja_id = self.obtener_hoja_id(hoja_seleccionada[1])
                            if hoja_id:
                                permisos = self.ver_hoja(hoja_id)
                                if permisos in ["lectura y escritura", "creador"]:
                                    self.editar_hoja(hoja_id)
                        else:
                            print("Opcion no valida.")
                elif opcion == '3':
                    if not self.hojas:
                        print("No tienes hojas de calculo disponibles para compartir.")
                    else:
                        self.compartir_hoja()
                else:
                    print("Opcion no valida.")
        except KeyboardInterrupt:
            print("\nSaliendo del cliente...")
        finally:
            self.stop_event.set()
            self.desconectar()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 cliente.py <usuario>")
        sys.exit(1)
    usuario = sys.argv[1]
    cliente = Cliente(usuario)
    cliente.run()
