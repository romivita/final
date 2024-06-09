class Comunicacion:
Clase para manejar la comunicacion entre el cliente y el servidor.

    Atributos:
        host (str): Direccion del host al que se conecta.
        port (int): Puerto al que se conecta.
        socket (socket): Socket para la comunicacion.
    
    Metodos:
        conectar():
            Conecta al host y puerto especificados.
        
        enviar_datos(mensaje):
            Envia un mensaje al host conectado.

            Args:
                mensaje (str): Mensaje a enviar.
        
        cerrar_conexion():
            Cierra la conexion con el host.
