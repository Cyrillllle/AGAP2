import sqlite3
import storage
from queue import Queue

def create_ddb(path) :
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (' \
                'id INTEGER PRIMARY KEY, ' \
                'first_name TEXT, ' \
                'last_name TEXT, ' \
                'username TEXT, ' \
                'cv_id INTEGER, ' \
                'cv_date TEXT, ' \
                'cv_udpated BOOL)')
    return True


def update_user_table(path) :
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute('INSER OR REPLACE INTO users (' \
                   'id, '
                   'name, '
                   ''
    ')')


def connect_ddb(path) :
    conn = conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;") 
    cursor = conn.cursor()
    return cursor

writer_queue = Queue()

def writer(path, write_func, **kwargs) :
    cursor = connect_ddb(path)
    buffer = []
    while True : 
        item = writer_queue.get()
        if item is None : 
            break
        buffer.append(item)

    if len(buffer) >= 50 :
        cursor.execute("BEGIN;")
        write_func(**kwargs)

