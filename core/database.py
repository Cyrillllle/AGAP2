import sqlite3
from core.storage import DB_PATH
import queue
import time
import threading



def connect_ddb(path) :
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;") 
    return conn



def init_db() :
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS users (' \
                'id INTEGER PRIMARY KEY, ' \
                'first_name TEXT, ' \
                'last_name TEXT, ' \
                'username TEXT, ' \
                'cv_id INTEGER, ' \
                'cv_date TEXT, ' \
                'cv_needs_parsing INTEGER)')
                    
    cursor.execute('CREATE TABLE IF NOT EXISTS cv_raw (' \
                'cv_id INTEGER PRIMARY KEY, ' \
                'data_raw BLOB)')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS cv_parsed (' \
                'cv_id INTEGER PRIMARY KEY, ' \
                'exp TEXT, ' \
                'skills TEXT)')
    
    cursor.close()
    conn.commit()
    conn.close()
    return True


def update_user_table(path) :
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute('INSER OR REPLACE INTO users (' \
                   'id, '
                   'name, '
                   ''
    ')')





def db_raw_writer(writer_queue, stop_event) :
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    last_commit = time.time()

    while not stop_event.is_set() or not writer_queue.empty() :
        try :
            task = writer_queue.get(timeout = 0.5)
        except queue.Empty :
            task = None

        if task :
            kind = task["type"] 

            if kind == "upsert_user" :
                cursor.execute('INSERT INTO users (id, first_name, last_name, username, cv_id, cv_date, cv_needs_parsing) ' \
                'VALUES (?, ?, ?, ?, ?, ?, ?) ' \
                'ON CONFLICT(id) DO UPDATE SET ' \
                    'cv_date = excluded.cv_date, ' \
                    'cv_id = excluded.cv_id, ' \
                    'cv_needs_parsing = excluded.cv_needs_parsing', task["data"])
                
            elif kind == "upsert_cv_raw" :
                cursor.execute('INSERT OR REPLACE INTO cv_raw (cv_id, data_raw )' \
                               'VALUES (?, ?)', task["data"])
                
            elif kind == "upsert_cv_parsed" :
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                cursor.execute("""
                               INSERT OR REPLACE INTO cv_parsed (cv_id, exp, skills) 
                               VALUES (?, ?, ?)""", task["data"])
            
            writer_queue.task_done()

        if time.time() - last_commit > 2 :
            conn.commit()
            last_commit = time.time()

    cursor.close()
    conn.commit()
    conn.close()

def start_writer() :
    q = queue.Queue()
    stop_event = threading.Event()
    t = threading.Thread(target=db_raw_writer, args=(q, stop_event), daemon=False)
    t.start()
    return q, stop_event, t


def load_users_cv_dates():
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, cv_date FROM users")
    rows = cursor.fetchall()

    conn.close()

    return {user_id: cv_date for user_id, cv_date in rows}



def get_total_cv_parsing() :
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT SUM(CASE WHEN cv_needs_parsing > 0 THEN 1 ELSE 0 END)
                   FROM users
                   """)
    
    return cursor.fetchone()[0]



def read_raw_data(batch_size = 50) :
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT r.cv_id, r.data_raw
                   FROM cv_raw r
                   LEFT JOIN cv_parsed p ON r.cv_id = p.cv_id
                   WHERE p.cv_id IS NULL
                   """)

    while True :
        rows = cursor.fetchmany(batch_size)
        if not rows :
            break
        for cv_id, data_raw in rows :
            yield cv_id, data_raw

    cursor.close()
    conn.close()