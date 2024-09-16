Aplicación cliente-servidor que permite la gestión y colaboración en hojas de cálculo de manera
remota. El cliente envía solicitudes para realizar operaciones sobre hojas de cálculo, el servidor recibe esas
solicitudes, realiza las operaciones necesarias y devuelve los resultados
al cliente. La comunicación entre cliente y servidor se realiza a través de sockets TCP, utilizando mensajes en formato
JSON.

El sistema implementa concurrencia para manejar múltiples clientes, donde cada conexión de cliente
es gestionada en su propio hilo. En cuanto al manejo de datos, el servidor
utiliza una base de datos SQLite para gestionar usuarios, hojas de cálculo y permisos de acceso.

## Gráfico de la Arquitectura
```
                     +-------------------+     +-------------------+
                     |    Cliente 1      |     |    Cliente N      |
                     +-------------------+     +-------------------+
                                |                        |
                                |                        |
                                |                        |
                            +-------------------------------+                
                            |         Comunicación          |                
                            +-------------------------------+                
                                       | IPC (Sockets TCP)                  
                                       |
                              +------------------------+
                              |      Servidor          |
                              +------------------------+
                              |                        |
                              | +--------------------+ |
                              | | Base de Datos      | |
                              | | (SQLite)           | |
                              | +--------------------+ |
                              |                        |
                              +------------------------+
                              |                        |
                +----------------------+    +----------------------+
                | Procesamiento        |    | Gestión de Hojas de  |
                | de Mensajes          |    | Cálculo              |
                +----------------------+    +----------------------+
```