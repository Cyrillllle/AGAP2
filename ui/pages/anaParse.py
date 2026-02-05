import streamlit as st
import pathlib
import os
import sqlite3
from queue import Queue
import json
import shelve
import time
import threading
import io
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

from api.client import api_request, RequestType, GetAllUsers, GetUserCv, ExportCv
from core.storage import USER_DATA_DIR, TOKEN_PATH
from core.database import init_db, start_writer, load_users_cv_dates
from core.parser import *


@dataclass
class JobState:
    running         : bool = False
    stop_requested  : bool = False
    progress        : float = 0.0
    message         : str = ""
    error           : str | None = None
    done            : bool = False

if "job_state" not in st.session_state:
    st.session_state.job_state = JobState()

if "worker_thread" not in st.session_state:
    st.session_state.worker_thread = None



def parse_worker(state: JobState):
    treated = 0
    total = 200  # ou mieux : count SQL

    for cv_id, cv_raw in read_raw_data():
        if state.stop_requested:
            break

        xp, skills = parse_cv(cv_raw)
        treated += 1
        state.progress = treated / total      

        if skills == [] :
            print(cv_id)


    state.done = True
    state.running = False


def start_job():
    state = st.session_state.job_state
    state.running = True
    state.stop_requested = False
    state.progress = 0.0
    state.message = "Démarrage..."
    state.done = False
    state.error = None

    init_db()

    existing_users = load_users_cv_dates()

    writer_queue, stop_event, writer_thread = start_writer()


    t = threading.Thread(target=parse_worker, args=(state,), daemon=True)

    t.start()

    st.session_state.worker_thread = t
    

def stop_job():
    st.session_state.job_state.stop_requested = True


def render():
    state = st.session_state.job_state

    st.title("Analyse des données")

    if not state.running:
        st.button("Analyser les profils", on_click=start_job)
    else:
        st.button("Stop", on_click=stop_job)

    if state.running:
        st.progress(state.progress, text=state.message)
        st_autorefresh(interval=500, key="refresh_job")

    if state.done:
        st.success("Traitement terminé")

    if state.error:
        st.error(state.error)
