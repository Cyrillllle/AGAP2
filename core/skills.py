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



def update_skills_db() : 
    writer_queue, stop_event, writer_thread = start_writer()
    skills = read_skills_json()
    for category in skills :
        for skill in skills[category] :
            writer_queue.put({"type": "upsert_skills", "data": (skill, category)})
