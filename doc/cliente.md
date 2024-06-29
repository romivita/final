class Cliente:
Clase que representa el cliente que se conecta a un servidor para actualizar una hoja de calculo.

    Atributos:
        host (str): Direccion del host del servidor.
        port (int): Puerto del servidor.
        nombre_hoja (str): Nombre de la hoja de calculo.
        comunicacion (Comunicacion): Instancia de la clase Comunicacion para gestionar la comunicacion con el servidor.

    Metodos:
        conectar_servidor():
            Conecta el cliente al servidor y envia el nombre de la hoja de calculo.

        cerrar_conexion():
            Cierra la conexion con el servidor.

        actualizar_celda(fila, columna, valor):
            Envia una actualizacion de celda al servidor.
            
            Args:
                fila (int): Numero de fila de la celda.
                columna (int): Numero de columna de la celda.
                valor (str): Valor de la celda.

        iniciar_interaccion():
            Inicia la interaccion con el usuario para ingresar datos de la hoja de calculo.
