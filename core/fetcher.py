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


@dataclass
class JobState:
    running         : bool = False
    stop_requested  : bool = False
    progress        : float = 0.0
    message         : str = ""
    error           : str | None = None
    done            : bool = False

Selection_url = {
    "IT"        : "dc-it.",
    "Industrie" : "dc."
}

if "job_state_fetch" not in st.session_state:
    st.session_state.job_state_fetch = JobState()

if "worker_thread" not in st.session_state:
    st.session_state.worker_thread = None


def process_user(user, api_key, api_secret, existing_users, writer_queue, selection):
    start_time = time.time()
    # récupérer les CV
    response = api_request(
        api_secret,
        RequestType.GET_USER_CV,
        GetUserCv(api_key, "", user["id"])
    )

    cvs = json.loads(response.text)

    latest_cv_id = None
    needs_parsing = 0
    latest_date = datetime.fromisoformat("2000-01-01T01:01:01+01:00")

    for item in cvs:
        try :
            cv_date = datetime.fromisoformat(item["updated"])
            cv_url = item["public_url"]
            if cv_date > latest_date:
                latest_date = cv_date
                latest_cv_id = item["id"]
                cv_url = item["public_url"]
                cv_completion = item["completion"]
        except Exception as e:
            print(e)
    
    skip_user = True
    try :
        if selection == "all" or Selection_url[selection] in cv_url :
            skip_user = False
    except Exception as e :
        print(e)
    
    if skip_user :
        return start_time

    if not latest_cv_id or not cv_completion :
        latest_cv_date = None
        needs_parsing = 0
        try :
            writer_queue.put({"type": "upsert_user", "data": (user["id"],
                                                        user["firstname"],
                                                        user["lastname"],
                                                        user["username"],
                                                        latest_cv_id,
                                                        latest_cv_date,
                                                        needs_parsing)})
        except Exception as e :
            print(e)
        return start_time

    else : 
        db_cv_date = existing_users.get(user["id"])
        latest_db_cv_date = 0
        if db_cv_date != None :
            latest_db_cv_date = datetime.fromisoformat(db_cv_date)

        if latest_date != latest_db_cv_date :
            response = api_request(
                api_secret,
                RequestType.EXPORT_CV,
                ExportCv(api_key, "", latest_cv_id)
            )

            if response.status_code == 200 :
                doc_bytes = response.content
                writer_queue.put({"type": "upsert_cv_raw", "data": (latest_cv_id, doc_bytes)})
                needs_parsing = 1
                latest_cv_date = latest_date.isoformat()
            else : 
                latest_cv_id = None
                latest_cv_date = None
                needs_parsing = 0

            try :
                writer_queue.put({"type": "upsert_user", "data": (user["id"],
                                                            user["firstname"],
                                                            user["lastname"],
                                                            user["username"],
                                                            latest_cv_id,
                                                            latest_cv_date,
                                                            needs_parsing)})
            except Exception as e :
                print(e)

    return start_time


def fetch_profiles_worker(pipelineManager, api_key, api_secret, existing_users, writer_queue, selection):
    try:
        pipelineManager.message = "Initialisation..."

        users = []
        total = 1
        start = time.time()
        timeout = 60
        page = 1
        while len(users) < total :
            response = api_request(
                api_secret,
                RequestType.GET_ALL_USERS,
                GetAllUsers(api_key, "", "user", page, 100)
            )

            data = json.loads(response.text)
            users = users + data["users"]
            total = data["total"]
            timeout = total / 100
            elapsed_time = time.time() - start

            page += 1

            if elapsed_time > timeout :
                print("message d'erreur")
                break

        treated = 0
        total = len(users)
        start_time = time.time()
        total_time = 0


        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(process_user, user, api_key, api_secret, existing_users, writer_queue, selection)
                for user in users
            ]

            for future in as_completed(futures):
                # if state._stop_event:
                #     state.message = "Arrêt demandé"
                #     break

                future.result()  # lève erreur si besoin
                treated += 1
                elapsed_time = time.time() - start_time
                pipelineManager.progress = treated / total
                total_time = total_time + elapsed_time
                mean_treatmment_time = total_time / treated
                remaining_time = mean_treatmment_time * (total - treated)
                if remaining_time >= 60 :
                    estimation_mn = str(int(remaining_time/60))+"mn"
                else : 
                    estimation_mn = ""
                estimation_sec = str(int((remaining_time%60))) + "s"
                estimation = estimation_mn + estimation_sec
                    
                pipelineManager.message = f"{treated}/{total} profils traités. Environ {estimation} restantes"
                start_time = time.time()

    except Exception as e:
        pipelineManager.error = str(e)
        print(e)

    finally :
        print(("finally fetcher"))
        pipelineManager.step += 1



def start_fetch(pipelineManager, selection, stop_requested):
    pm = pipelineManager
    # state.stop_requested = False
    
    pm.message = "Démarrage..."

    token = shelve.open(str(TOKEN_PATH))
    api_key = token["api_key"]
    api_secret = token["api_secret"]

    try : 

        init_db()

        existing_users = load_users_cv_dates()

        writer_queue, stop_event, writer_thread = start_writer()


        fetch_profiles_worker(pm, api_key, api_secret, existing_users, writer_queue, selection)
    except Exception as e : 
        print(e)
