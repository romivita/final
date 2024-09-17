# Final Computación 2

## Instrucciones para clonar y lanzar la aplicación

1. **Requisitos:**

- Python 3.8 o superior.
- Paquetes necesarios:
    - sqlite3
    - configparser
    - logging
    - socket
    - json

2. **Clonar el repositorio:**

```bash
git clone https://github.com/romivita/final
cd app
```

3. **Configurar `config.ini`:**

```
[DEFAULT]
host = localhost
port = 55011
```

4. **Iniciar el servidor:**

`server/main.py`

_Parámetros opcionales:_

--host: Host del servidor (por defecto: localhost).

--port: Puerto del servidor (por defecto: 55011).

5. **Iniciar un cliente:**

`client/cliente.py --user <usuario>`

_Parámetros opcionales:_

--host: Host del servidor (por defecto: localhost).

--port: Puerto del servidor (por defecto: 55011).
