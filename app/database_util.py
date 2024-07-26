import sqlite3


def inicializar_bd():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            usuario TEXT UNIQUE,
                            pwd_hash TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS hojas_calculo (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nombre TEXT,
                            creador_id INTEGER,
                            FOREIGN KEY (creador_id) REFERENCES usuarios (id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS permisos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    cursor.execute('''SELECT hojas_calculo.id, hojas_calculo.nombre FROM hojas_calculo
                      JOIN permisos ON hojas_calculo.id = permisos.hoja_id
                      WHERE permisos.usuario_id = ?''', (usuario_id,))
    hojas = cursor.fetchall()
    conn.close()
    return [{"id": hoja[0], "nombre": hoja[1]} for hoja in hojas]


def crear_hoja_bd(nombre_hoja, usuario_id):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO hojas_calculo (nombre, creador_id) VALUES (?, ?)', (nombre_hoja, usuario_id))
        hoja_id = cursor.lastrowid
        cursor.execute('INSERT INTO permisos (hoja_id, usuario_id, permisos) VALUES (?, ?, ?)',
                       (hoja_id, usuario_id, 'lectura-escritura'))
        conn.commit()
        conn.close()
        print(f"Hoja de calculo '{nombre_hoja}' creada para el usuario ID '{usuario_id}' en la base de datos.")
        return hoja_id
    except sqlite3.Error as e:
        print(f"Error al crear la hoja de calculo: {e}")
        raise


def hoja_existe_bd(hoja_id, usuario_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT COUNT(*) FROM hojas_calculo
                      JOIN permisos ON hojas_calculo.id = permisos.hoja_id
                      WHERE hojas_calculo.id = ? AND permisos.usuario_id = ?''', (hoja_id, usuario_id))
    conteo = cursor.fetchone()[0]
    conn.close()
    return conteo > 0


def compartir_hoja_bd(hoja_id, usuario_compartido, usuario_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario_compartido,))
    usuario_compartido_id = cursor.fetchone()
    if usuario_compartido_id:
        usuario_compartido_id = usuario_compartido_id[0]
        cursor.execute('SELECT id FROM hojas_calculo WHERE id = ? AND creador_id = ?', (hoja_id, usuario_id))
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
            return {"error": f"La hoja de calculo '{hoja_id}' no existe o no tienes permiso para compartirla"}
    else:
        conn.close()
        return {"error": f"El usuario {usuario_compartido} no existe"}


def usuario_existe(usuario):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else None


def crear_usuario(usuario, pwd_hash):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO usuarios (usuario, pwd_hash) VALUES (?, ?)', (usuario, pwd_hash))
        conn.commit()
        usuario_id = cursor.lastrowid
        conn.close()
        return usuario_id
    except sqlite3.IntegrityError:
        return None
