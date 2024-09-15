# Servidor

Recibe los comandos del cliente, valida los datos, ejecuta las operaciones solicitadas, interactúa con la base de datos
para almacenar y recuperar información, y devuelve los resultados al cliente.

* **Manejo de conexiones concurrentes**: Utiliza hilos para manejar múltiples clientes conectados de manera simultánea.
* **Autenticación de usuarios**: Gestiona el inicio de sesión y la creación de nuevas cuentas.
* **Gestión de hojas de cálculo**: Crea, elimina, lista y comparte hojas de cálculo. Además, otorga permisos según el
  rol del usuario (propietario, lectura, escritura).
* **Ediciones concurrentes**: Utiliza una cola de ediciones para procesar de manera asincrónica las modificaciones de
  las celdas y asegurarse de que se apliquen de manera correcta.
* **Sincronización de cambios**: Envía actualizaciones a todos los clientes conectados a una hoja de cálculo cuando se
  realizan cambios en las celdas.
* **Manejo de archivos CSV**: Almacena y actualiza los datos de las hojas de cálculo en archivos CSV.

### Autenticación

* **Inicio de sesión**: Verifica si el usuario existe y si la contraseña es correcta.
* **Creación de cuenta**: Registra un nuevo usuario en la base de datos, con su nombre de usuario y un hash de su
  contraseña.

### Cola de Ediciones

* **Agrega ediciones**: Recibe mensajes de edición (hoja, celda, valor, usuario) de los clientes y los coloca en la
  cola.
* **Procesa ediciones**: Extrae ediciones de la cola y las aplica a los archivos CSV correspondientes.
* **Notifica cambios**: Una vez aplicados los cambios, notifica a todos los clientes conectados a esa hoja para que
  actualicen su visualización de la hoja de cálculo.

### Gestor de Hojas

* **Crear hojas**: Crea una nueva hoja de cálculo para el usuario en la base de datos y genera un archivo CSV
  correspondiente.
* **Listar hojas**: Muestra al usuario todas las hojas en las que tiene permisos, organizadas por tipo de acceso (
  propietario, lectura y escritura, solo lectura).
* **Compartir hojas**: Permite a los usuarios compartir sus hojas con otros usuarios, asignándoles permisos de lectura o
  escritura.
* **Eliminar hojas**: Elimina una hoja de cálculo, incluyendo el archivo CSV y los permisos asociados.
