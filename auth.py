import sqlite3
import hashlib

def conectar_db():
    conn = sqlite3.connect('usuarios.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    conn.commit()
    return conn

def hash_pw(pw):
    return hashlib.sha256(str.encode(pw)).hexdigest()

def registrar_usuario(u, p):
    if u == "" or p == "": return False
    conn = conectar_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users VALUES (?,?)', (u, hash_pw(p)))
        conn.commit()
        return True
    except:
        return False

def validar_login(u, p):
    conn = conectar_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (u, hash_pw(p)))
    return c.fetchone()