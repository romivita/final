#!/opt/homebrew/bin/python3
import argparse
import logging

from config_util import cargar_configuracion
from database_util import init_db
from servidor import Servidor

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    config_host, config_port = cargar_configuracion()

    init_db()

    parser = argparse.ArgumentParser(description="servidor de hojas de calculo")
    parser.add_argument('--host', default=config_host, help="host del servidor")
    parser.add_argument('--port', type=int, default=config_port, help="puerto del servidor")

    args = parser.parse_args()

    servidor = Servidor(host=args.host, port=args.port)
    servidor.iniciar()
