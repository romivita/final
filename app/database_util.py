import sqlite3


def init_db():
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


def query_db(query, args=(), one=False):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(query, args)
    rv = cursor.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv


init_db()
