# Comunicacion

Esta clase estática maneja la comunicación entre el cliente y el servidor a través de sockets, utilizando mensajes en
formato JSON.

* `manejar_excepciones(func)`
  Este decorador se encarga de manejar las excepciones que puedan ocurrir en las funciones decoradas. Atrapa errores
  comunes, como problemas de conexión con el socket y errores en el manejo de JSON, además de cualquier excepción
  inesperada. Registra los errores en el log y vuelve a lanzar la excepción para que sea manejada adecuadamente en otros
  niveles.


* Método `enviar_mensaje(mensaje, conn)`: Envía un mensaje (en formato de diccionario) a través de una conexión de
  socket.


* Método `Método recibir_mensaje(conn, buffer_size=4096)`: Recibe un mensaje desde un socket y lo convierte de JSON a un
  diccionario.


* Método `Método enviar_y_recibir(mensaje, conn, buffer_size=4096)`: Envía un mensaje y luego espera una respuesta en la
  misma conexión.
