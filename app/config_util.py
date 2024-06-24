import json
import os


def obtener_ruta_configuracion():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fixtures/config.json'))


def cargar_configuracion():
    ruta_config = obtener_ruta_configuracion()
    file = None
    try:
        file = open(ruta_config, "r")
        config = json.load(file)
        return config["host"], config["port"]
    except FileNotFoundError:
        print(f"Archivo de configuración no encontrado en {ruta_config}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"Error al decodificar el archivo JSON: {e}")
        return None, None
    finally:
        if file:
            file.close()
