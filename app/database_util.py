import sqlite3


class Database:
    def __init__(self, db_name='database.db'):
        self.db_name = db_name

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def query(self, query, args=(), one=False):
        self.cursor.execute(query, args)
        rv = self.cursor.fetchall()
        return (rv[0] if rv else None) if one else rv

    def execute(self, query, args=()):
        self.cursor.execute(query, args)
        return self.cursor


def init_db():
    with Database() as db:
        db.query('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT UNIQUE,
                        pwd_hash TEXT)''')
        db.query('''CREATE TABLE IF NOT EXISTS hojas_calculo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT,
                        creador_id INTEGER,
                        FOREIGN KEY (creador_id) REFERENCES usuarios (id))''')
        db.query('''CREATE TABLE IF NOT EXISTS permisos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hoja_id INTEGER,
                        usuario_id INTEGER,
                        permisos TEXT,
                        FOREIGN KEY (hoja_id) REFERENCES hojas_calculo (id),
                        FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
                        UNIQUE(hoja_id, usuario_id))''')
