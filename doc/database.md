# Database

Esta clase utiliza un contexto (`__enter__` y `__exit__`) para manejar de manera segura las conexiones a una base de
datos SQLite. Esto asegura que las transacciones se confirmen o reviertan dependiendo de si ocurren excepciones durante
su uso

* Método `query(query, args=(), one=False)`: Ejecuta una consulta SQL y devuelve el resultado.

* Método `execute(query, args=())`: Ejecuta una sentencia SQL (por ejemplo, INSERT, UPDATE, DELETE).

**Función** `init_db()`: Inicializa la base de datos creando las tablas necesarias (usuarios, hojas de cálculo y
permisos). Utiliza la clase Database para asegurarse de que las operaciones se manejen correctamente.