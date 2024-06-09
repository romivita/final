class Servidor:
Clase que representa el servidor que gestiona multiples hojas de calculo para diferentes clientes.

    Atributos:
        host (str): Direccion del host donde se ejecuta el servidor.
        port (int): Puerto en el que el servidor escucha.
        clientes (list): Lista de clientes conectados.
        hojas_calculo (dict): Diccionario que contiene las hojas de calculo de todos los clientes.
        socket_servidor (socket): Socket del servidor para aceptar conexiones.

    Metodos:
        __init__(self):
            Inicializa el servidor leyendo la configuracion desde un archivo JSON.

        manejar_cliente(cliente_socket, cliente_address):
            Maneja la conexion con un cliente especifico.

            Args:
                cliente_socket (socket): Socket del cliente.
                cliente_address (tuple): Direccion del cliente.

        guardar_en_csv(hoja_nombre):
            Guarda los datos de la hoja de calculo especificada en un archivo CSV.

            Args:
            hoja_nombre (str): Nombre de la hoja de calculo.

        iniciar():
            Inicia el servidor y espera conexiones entrantes.