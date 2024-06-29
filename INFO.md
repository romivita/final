INFO.md: contendrá un breve informe sobre las decisiones principales de diseño del sistema, y su justificación (ej, por
qué un determinado modelo de datos, o tipo de almacenamiento, o uso de multiproceso/multithread, etc).
1. Modelo de Datos: Hoja de Cálculo basada en Diccionario para representar la hoja de cálculo en memoria, con las celdas como claves y sus contenidos como valores.

* Eficiencia: Los diccionarios proporcionan acceso rápido a los datos mediante claves, lo que es esencial para la actualización y consulta de celdas.
* Flexibilidad: Permite manejar celdas dispersas sin necesidad de almacenar una gran matriz de valores vacíos, optimizando así el uso de memoria.

2. Almacenamiento: Archivos CSV para la persistencia de datos.

* Compatibilidad: Los archivos CSV son ampliamente compatibles y pueden ser abiertos y editados con numerosas herramientas y aplicaciones.
* Simplicidad: Facilita la importación y exportación de datos sin la necesidad de una base de datos compleja.
* Eficiencia: Para el volumen de datos esperado, los archivos CSV proporcionan una solución simple y eficaz.

3. Comunicación: Sockets TCP para la comunicación entre clientes y el servidor.

* Fiabilidad: TCP garantiza la entrega de paquetes en el orden correcto, lo cual es crucial para mantener la consistencia de la hoja de cálculo entre múltiples clientes.
* Simplicidad de Implementación: La biblioteca de sockets de Python facilita la implementación y gestión de las conexiones.

4. Concurrencia: Multithreading para manejar la concurrencia tanto en el servidor como en el cliente.

* Manejo de Múltiples Clientes: Los hilos permiten al servidor atender múltiples conexiones de clientes simultáneamente, mejorando la capacidad de respuesta.
* Simultaneidad: En el cliente, los hilos permiten recibir actualizaciones en tiempo real mientras el usuario interactúa con la aplicación.
* Simplicidad: La programación con hilos en Python es más sencilla en comparación con la programación multiproceso, especialmente debido a la Global Interpreter Lock (GIL) que simplifica la gestión de recursos compartidos.

5. Sincronización: Uso de Cola (Queue) y Bloqueos (Locks)
Emplear una cola para procesar actualizaciones de celdas y bloqueos para asegurar la consistencia de los datos.

* Orden de Procesamiento: La cola garantiza que las actualizaciones se procesen en el orden en que se reciben, preservando la integridad de los datos.
* Consistencia: Los bloqueos aseguran que las operaciones en la hoja de cálculo sean atómicas, evitando condiciones de carrera y asegurando la consistencia de los datos.