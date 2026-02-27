import sqlite3
from core.storage import DB_PATH, SKILLS_PATH
import json
import queue
import time
import threading



def connect_ddb(path) :
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;") 
    conn.execute("PRAGMA foreign_keys = ON;") 
    return conn



def init_db() :
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS users (' \
                'id INTEGER PRIMARY KEY, ' \
                'first_name TEXT, ' \
                'last_name TEXT, ' \
                'username TEXT)')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS cv (' \
                'id INTEGER PRIMARY KEY, ' \
                'user_id INTEGER UNIQUE, ' \
                'cv_date TEXT, ' \
                'needs_parsing INTEGER,' \
                'FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)')
                    
    cursor.execute('CREATE TABLE IF NOT EXISTS cv_raw (' \
                'cv_id INTEGER PRIMARY KEY, ' \
                'data_raw BLOB, ' \
                'cv_pdf BLOB, ' \
                'FOREIGN KEY(cv_id) REFERENCES cv(id) ON DELETE CASCADE)')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS cv_parsed (' \
                'cv_id INTEGER PRIMARY KEY, ' \
                'exp TEXT, ' \
                'skills TEXT,' \
                'FOREIGN KEY(cv_id) REFERENCES cv(id) ON DELETE CASCADE)')
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                category TEXT
                )""")
        
    cursor.execute(f'CREATE TABLE IF NOT EXISTS cv_skill (' \
                'cv_id INTEGER, ' \
                'skill_id INTEGER, ' \
                'months INTEGER, ' \
                'PRIMARY KEY(cv_id, skill_id),' \
                'FOREIGN KEY(cv_id) REFERENCES cv(id) ON DELETE CASCADE, ' \
                'FOREIGN KEY(skill_id) REFERENCES skills(id))')
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_skill_name ON skills(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cv_user_id ON cv(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cvskill_skill_id ON cv_skill(skill_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cvskill_cv_id ON cv_skill(cv_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cvskill_months ON cv_skill(months)")
    print("init done")
    cursor.close()
    conn.commit()
    conn.close()
    return True



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
                print("upsert user")
                cursor.execute('INSERT INTO users (id, first_name, last_name, username) ' \
                'VALUES (?, ?, ?, ?) ' \
                'ON CONFLICT(id) DO UPDATE SET ' \
                    'first_name = excluded.first_name, ' \
                    'last_name = excluded.last_name, ' \
                    'username = excluded.username', task["data"])
            
            elif kind == "upsert_cv" :
                print("upsert cv")
                cursor.execute('INSERT INTO cv (id, user_id, cv_date, needs_parsing)' \
                            'VALUES (?, ?, ?, ?) '
                            'ON CONFLICT(user_id) DO UPDATE SET ' \
                                    'cv_date = excluded.cv_date, ' \
                                    'needs_parsing = excluded.needs_parsing', task["data"])
                
            elif kind == "upsert_cv_raw" :
                cursor.execute('INSERT INTO cv_raw (cv_id, data_raw, cv_pdf )' \
                            'VALUES (?, ?, ?) ' \
                                'ON CONFLICT(cv_id) DO UPDATE SET ' \
                                '   data_raw = excluded.data_raw, ' \
                                '   cv_pdf = excluded.cv_pdf', task["data"])
                
            elif kind == "upsert_cv_parsed" :
                cursor.execute("""
                            INSERT INTO cv_parsed (cv_id, exp, skills) 
                            VALUES (?, ?, ?) 
                            ON CONFLICT(cv_id) DO UPDATE SET 
                                    exp = excluded.exp, 
                                    skills = excluded.skills""", task["data"])
                
            elif kind == "upsert_skills" :
                cursor.execute("""
                            INSERT INTO skills (name, category) 
                            VALUES (?, ?) 
                            ON CONFLICT(name) DO UPDATE SET 
                                    category = excluded.category""", task["data"])
                
            elif kind == "upsert_cv_skill" : 
                cursor.execute("""
                            INSERT INTO cv_skill (cv_id, skill_id, months) 
                            VALUES (?, ?, ?) 
                            ON CONFLICT(cv_id, skill_id) DO UPDATE SET 
                                    months = excluded.months""", task["data"])
                
            
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

    cursor.execute("""SELECT u.id, c.cv_date 
                   FROM users u 
                   LEFT JOIN cv c ON c.user_id = u.id""")
    rows = cursor.fetchall()

    conn.close()

    return {user_id: cv_date for user_id, cv_date in rows}



def get_total_cv_parsing() :
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT SUM(CASE WHEN needs_parsing > 0 THEN 1 ELSE 0 END)
                   FROM cv
                   """)
    
    return cursor.fetchone()[0]



def read_raw_data(batch_size = 50) :
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT r.cv_id, r.data_raw
                   FROM cv_raw r
                   LEFT JOIN cv c ON r.cv_id = c.id
                   WHERE c.needs_parsing = 1
                   """)

    while True :
        rows = cursor.fetchmany(batch_size)
        if not rows :
            print("here1")
            break
        for cv_id, data_raw in rows :
            yield cv_id, data_raw

    cursor.close()
    conn.close()


def cv_raw_exists(cv_id):
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT EXISTS(
            SELECT 1
            FROM cv_raw
            WHERE cv_id = ?
        )
    """, (cv_id,))

    exists = cursor.fetchone()[0] == 1

    cursor.close()
    conn.close()
    return exists


def read_parsed_data(batch_size = 50) :
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT r.cv_id, r.exp, r.skills
                   FROM cv_parsed r
                   LEFT JOIN cv c ON r.cv_id = c.id
                   WHERE c.needs_parsing = 1
                   """)

    while True :
        rows = cursor.fetchmany(batch_size)
        if not rows :
            break
        for cv_id, exp, skills in rows :
            yield cv_id, exp, skills

    cursor.close()
    conn.close()


def read_skills(batch_size = 50) :
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT r.id, r.name
                   FROM skills r
                   """)
    
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {skill_id: skill_name for skill_id, skill_name in rows}



def temp() :
    print("suppression")
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""DELETE FROM cv_skill""")
    
    conn.commit()
    cursor.close()
    conn.close()


# def search(skill, nb_months) :
#     conn = connect_ddb(DB_PATH)
#     cursor = conn.cursor()
    
#     cursor.execute("""SELECT u.id, u.first_name, u.last_name
#                     FROM users u
#                     WHERE u.id IN (
#                     SELECT c.user_id
#                     FROM cv c
#                     JOIN cv_skill cs ON cs.cv_id = c.id
#                     JOIN skills s ON s.id = cs.skill_id
#                     WHERE s.name = ? AND cs.months >= ?)""",(skill, nb_months))
#     rows = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     return {user_id : user_name for user_id, user_name in rows}


def search_multi(required_skills, optional_skills, min_months):
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()

    req_placeholders = ",".join("?" for _ in required_skills)
    opt_placeholders = ",".join("?" for _ in optional_skills) if optional_skills else ""

    all_skills = required_skills + optional_skills
    all_placeholders = ",".join("?" for _ in all_skills)

    query = f"""
    WITH filtered AS (
        SELECT 
            u.id,
            u.first_name,
            u.last_name,
            s.name,
            cs.months
        FROM users u
        JOIN cv c ON c.user_id = u.id
        JOIN cv_skill cs ON cs.cv_id = c.id
        JOIN skills s ON s.id = cs.skill_id
        WHERE s.name IN ({all_placeholders})
          AND cs.months >= ?
    ),
    scored AS (
        SELECT
            id,
            first_name,
            last_name,
            SUM(
                CASE
                    WHEN name IN ({req_placeholders}) THEN months
                    WHEN name IN ({opt_placeholders}) THEN months + 10
                    ELSE 0
                END
            ) AS score,
            COUNT(DISTINCT CASE
                WHEN name IN ({req_placeholders}) THEN name
            END) AS required_count
        FROM filtered
        GROUP BY id
    )
    SELECT id, first_name, last_name
    FROM scored
    WHERE required_count = ?
    ORDER BY score DESC
    """

    params = (
        all_skills +
        [min_months] +
        required_skills +
        optional_skills +
        required_skills +
        [len(required_skills)]
    )

    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [f"{first} {last}" for _, first, last in rows]