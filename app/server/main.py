#!/opt/homebrew/bin/python3
import argparse

from config_util import cargar_configuracion
from servidor import Servidor

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="servidor de hojas de calculo")
    parser.add_argument('--host', help="host del servidor")
    parser.add_argument('--port', type=int, help="puerto del servidor")

    args = parser.parse_args()

    if not args.host or not args.port:
        config_host, config_port = cargar_configuracion()

        if not args.host:
            args.host = config_host
        if not args.port:
            args.port = config_port

    servidor = Servidor(host=args.host, port=args.port)
    servidor.iniciar()
