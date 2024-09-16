1. **Modelo Cliente-Servidor**: para centralizar el control de las hojas de cálculo y permitir que varios usuarios
   trabajen juntos desde diferentes ubicaciones. Los clientes se conectan a un servidor que maneja todo.

2. **Base de Datos SQLite**: es simple y no requiere configuración adicional para almacenar y gestionar datos.

3. **Concurrencia**: el servidor puede manejar varios clientes al mismo tiempo usando hilos para cada conexión.

4. **Comunicación con Sockets TCP y JSON**: los sockets TCP son fiables para la comunicación entre procesos y permiten
   manejar varias conexiones al mismo tiempo. Los mensajes se envían en formato JSON, que es fácil de estructurar y
   procesar.

5. **Manejo de Hojas de Cálculo**: para evaluar celdas, usamos `ast` para garantizar seguridad y evitar la ejecución de
   código arbitrario.
