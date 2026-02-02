import streamlit as st
import pathlib
import os
import sqlite3
from queue import Queue
import json
import shelve
import time
import threading
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

from api.client import api_request, RequestType, GetAllUsers, GetUserCv, ExportCv
from core.storage import USER_DATA_DIR, TOKEN_PATH


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


def process_user(user, api_key, api_secret):
    start_time = time.time()
    # récupérer les CV
    response = api_request(
        api_secret,
        RequestType.GET_USER_CV,
        GetUserCv(api_key, "", user["id"])
    )

    cvs = json.loads(response.text)

    latest_cv_id = None
    latest_date = datetime.fromisoformat("2000-01-01T01:01:01+01:00")

    for item in cvs:
        cv_date = datetime.fromisoformat(item["updated"])
        if cv_date > latest_date:
            latest_date = cv_date
            latest_cv_id = item["id"]

    if not latest_cv_id:
        return

    response = api_request(
        api_secret,
        RequestType.EXPORT_CV,
        ExportCv(api_key, "", latest_cv_id)
    )
    with open(f"{USER_DATA_DIR}\\CV_n_{latest_cv_id}.docx", "wb") as f:
        f.write(response.content)

    return start_time


def fetch_profiles_worker(state: JobState, api_key, api_secret):
    try:
        state.running = True
        state.message = "Initialisation..."

        users = []
        total = 1
        start = time.time()
        timeout = 60
        page = 1
        while len(users) != total :
            response = api_request(
                api_secret,
                RequestType.GET_ALL_USERS,
                GetAllUsers(api_key, "", "user", page, 100)
            )

            data = json.loads(response.text)
            users = users + data["users"]
            total = data["total"]
            elapsed_time = time.time() - start

            page += 1

            if elapsed_time > timeout :
                print("message d'erreur")
                break

        treated = 0
        start_time = time.time()
        total_time = 0
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(process_user, user, api_key, api_secret)
                for user in users
            ]

            for future in as_completed(futures):
                if state.stop_requested:
                    state.message = "Arrêt demandé"
                    break

                future.result()  # lève erreur si besoin
                treated += 1
                elapsed_time = time.time() - start_time
                state.progress = treated / total
                total_time = total_time + elapsed_time
                mean_treatmment_time = total_time / treated
                remaining_time = mean_treatmment_time * (total - treated)
                if remaining_time >= 60 :
                    estimation_mn = str(int(remaining_time/60))+"mn"
                else : 
                    estimation_mn = ""
                estimation_sec = str(int((remaining_time%60))) + "s"
                estimation = estimation_mn + estimation_sec
                    
                state.message = f"{estimation} restantes"
                start_time = time.time()

        state.done = True

    except Exception as e:
        state.error = str(e)
        print(e)

    finally:
        state.running = False


def start_job():
    state = st.session_state.job_state
    state.running = True
    state.stop_requested = False
    state.progress = 0.0
    state.message = "Démarrage..."
    state.done = False
    state.error = None

    token = shelve.open(str(TOKEN_PATH))
    api_key = token["api_key"]
    api_secret = token["api_secret"]

    t = threading.Thread(
        target=fetch_profiles_worker,
        args=(state, api_key, api_secret),
        daemon=True
    )
    t.start()

    st.session_state.worker_thread = t

def stop_job():
    st.session_state.job_state.stop_requested = True


def render():
    state = st.session_state.job_state

    st.title("Gestion de la base de données")

    if not state.running:
        st.button("Récupérer tous les profils", on_click=start_job)
    else:
        st.button("Stop", on_click=stop_job)

    if state.running:
        st.progress(state.progress, text=state.message)
        st_autorefresh(interval=500, key="refresh_job")
        

    if state.done:
        st.success("Traitement terminé")

    if state.error:
        st.error(state.error)
