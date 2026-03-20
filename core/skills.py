import streamlit as st
import pathlib
import os
import time
import docx
import re
import sqlite3
from queue import Queue
import json
import shelve
import time
import threading
import io
import json
from unidecode import unidecode
from datetime import datetime
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

from core.storage import USER_DATA_DIR, TOKEN_PATH
from core.database import *



def read_skills_json() : 
    file = open(SKILLS_PATH)
    skills = json.load(file)
    file.close()
    return skills



def update_skills_db():
    skills_json = read_skills_json()
    
    # Aplatit toutes les skills du JSON
    skills_in_json = {skill for category in skills_json for skill in skills_json[category]}
    
    conn = connect_ddb(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ",".join("?" for _ in skills_in_json)
    cursor.execute(f"""
        DELETE FROM skills 
        WHERE name NOT IN ({placeholders})
        AND id NOT IN (SELECT DISTINCT skill_id FROM cv_skill)
    """, list(skills_in_json))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    writer_queue, stop_event, writer_thread = start_writer()
    for category in skills_json:
        for skill in skills_json[category]:
            writer_queue.put({"type": "upsert_skills", "data": (skill, category)})
    
    writer_queue.join()
    stop_event.set()
    writer_thread.join()