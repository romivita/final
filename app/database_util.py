import sqlite3


def inicializar_base_datos():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            usuario TEXT UNIQUE,
                            pwd_hash TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS hojas_calculo (
                            id INTEGER PRIMARY KEY,
                            nombre TEXT,
                            creador_id INTEGER,
                            FOREIGN KEY (creador_id) REFERENCES usuarios (id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS permisos (
                            id INTEGER PRIMARY KEY,
                            hoja_id INTEGER,
                            usuario_id INTEGER,
                            permisos TEXT,
                            FOREIGN KEY (hoja_id) REFERENCES hojas_calculo (id),
                            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
                            UNIQUE(hoja_id, usuario_id))''')
        conn.commit()
        conn.close()
        print("Base de datos inicializada.")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")
        raise


def verificar_credenciales(usuario, pwd_hash):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE usuario = ? AND pwd_hash = ?', (usuario, pwd_hash))
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else None


def obtener_hojas_usuario(usuario_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT hojas_calculo.nombre FROM hojas_calculo
                      JOIN permisos ON hojas_calculo.id = permisos.hoja_id
                      WHERE permisos.usuario_id = ?''', (usuario_id,))
    hojas = cursor.fetchall()
    conn.close()
    return [hoja[0] for hoja in hojas]


def crear_hoja_en_base_de_datos(nombre_hoja, usuario_id):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO hojas_calculo (nombre, creador_id) VALUES (?, ?)', (nombre_hoja, usuario_id))
        hoja_id = cursor.lastrowid
        cursor.execute('INSERT INTO permisos (hoja_id, usuario_id, permisos) VALUES (?, ?, ?)',
                       (hoja_id, usuario_id, 'lectura-escritura'))
        conn.commit()
        conn.close()
        print(f"Hoja de cálculo '{nombre_hoja}' creada para el usuario ID '{usuario_id}' en la base de datos.")
    except sqlite3.Error as e:
        print(f"Error al crear la hoja de cálculo: {e}")
        raise


def hoja_existe_en_base_de_datos(nombre_hoja, usuario):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT COUNT(*) FROM hojas_calculo
                      JOIN permisos ON hojas_calculo.id = permisos.hoja_id
                      WHERE hojas_calculo.nombre = ? AND permisos.usuario_id = ?''', (nombre_hoja, usuario))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def compartir_hoja(nombre_hoja, usuario_compartido, usuario_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario_compartido,))
    usuario_compartido_id = cursor.fetchone()
    if usuario_compartido_id:
        usuario_compartido_id = usuario_compartido_id[0]
        cursor.execute('SELECT id FROM hojas_calculo WHERE nombre = ? AND creador_id = ?', (nombre_hoja, usuario_id))
        hoja_id = cursor.fetchone()
        if hoja_id:
            hoja_id = hoja_id[0]
            cursor.execute('INSERT OR IGNORE INTO permisos (hoja_id, usuario_id, permisos) VALUES (?, ?, ?)',
                           (hoja_id, usuario_compartido_id, 'lectura-escritura'))
            conn.commit()
            conn.close()
            return {"status": "OK"}
        else:
            conn.close()
            return {"error": f"La hoja de cálculo '{nombre_hoja}' no existe o no tiene permisos para compartirla"}
    else:
        conn.close()
        return {"error": f"El usuario {usuario_compartido} no existe"}


def usuario_existe(usuario):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,))
    resultado = cursor.fetchone()
    conn.close()
    print(f"usuario_existe - Usuario: {usuario}, Resultado: {resultado}")  # Mensaje de depuración
    return resultado[0] if resultado else None


def crear_usuario(usuario, pwd_hash):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO usuarios (usuario, pwd_hash) VALUES (?, ?)', (usuario, pwd_hash))
        conn.commit()
        usuario_id = cursor.lastrowid
        print(f"Resultado: {usuario_id}")  # Mensaje de depuración
        conn.close()
        return usuario_id
    except sqlite3.IntegrityError:
        return None
