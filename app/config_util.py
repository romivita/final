import configparser


def cargar_configuracion():
    config = configparser.ConfigParser()
    config.read('config.ini')
    host = config.get('DEFAULT', 'host')
    port = config.getint('DEFAULT', 'port')
    return host, port
