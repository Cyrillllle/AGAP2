import streamlit as st
import pathlib
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
    
    elapsed_time = time.time() - start_time

    return start_time


def fetch_profiles_worker(state: JobState, api_key, api_secret):
    try:
        state.running = True
        state.message = "Initialisation..."

        response = api_request(
            api_secret,
            RequestType.GET_ALL_USERS,
            GetAllUsers(api_key, "", "user", 1, 100)
        )

        data = json.loads(response.text)
        users = data["users"]
        total = data["total"]

        treated = 0
        treatment_time = 0
        start_treatment = 0
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
                state.progress = treated / 100
                total_time = total_time + elapsed_time
                # treatment_time = (treatment_time + time.time() - start_time)
                # print(treatment_time)
                mean_treatmment_time = total_time / treated
                remaining_time = mean_treatmment_time * (100 - treated)
                if remaining_time >= 60 :
                    estimation_mn = str(int(remaining_time/60))+"mn"
                else : 
                    estimation_mn = ""
                estimation_sec = str(int((remaining_time%60))) + "s"
                estimation = estimation_mn + estimation_sec
                    
                    # mean_treatment_time = (mean_treatment_time + elapsed_time)/treated
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




# if "worker_thread" not in st.session_state :
#     st.session_state.worker_thread = None
# if "fetch_state" not in st.session_state :
#     st.session_state.fetch_state = 0
# if "stage" not in st.session_state:
#     st.session_state.stage = 0
# if "stop_requested" not in st.session_state:
#     st.session_state.stop_requested = False

# def set_state(i):
#     if st.session_state.stage == 1 and i == 0 :
#         confirm_stop()
#     st.session_state.stage = i

# def request_stop():
#     st.session_state.stop_requested = True

# @st.dialog("Attention")
# def confirm_stop():
#     st.write("Le téléchargement de la base de données sera annulé")
#     if st.button("Confirmer"):
#         st.session_state.stop_requested = True
#         st.session_state.show_confirm = False
#         st.rerun()
#     if st.button("Annuler"):
#         st.session_state.show_confirm = False

# @st.dialog("Attention")
# def fetch_error_dialog() :
#     if st.session_state.fetch_state == 1 :
#         st.write("Aucun profil n'a pu être récupéré")
#     elif st.session_state.fetch_state == 2 :
#         st.write("Tous les profils n'ont pas pu être récupéré")
#     elif st.session_state.fetch_state == 3 :
#         st.write("Tous les profils n'ont pas pu être récupéré : délai dépassé")
#     if st.button("OK"):
#         st.session_state.fetch_state = 0
#         st.rerun()


# def fetch_profiles() :
#     currentPath = pathlib.Path(__file__).parent.resolve()
#     token = shelve.open(str(currentPath) + "\\" + "vault")

#     allProfiles = []
#     if st.session_state.stage == 1 :
#         st.button("Stop", on_click=request_stop)
#         status_code_user = 200
#         nbProfile = -1
#         page = 1
#         progress_bar = st.progress(0, text="Récupération des profils en cours. Temps restant estimé :")
#         timeout = 10
#         start_time = time.time()
#         treatment_time = 0
#         nb_treated = 0
#         while status_code_user == 200 and nbProfile != len(allProfiles) :
#             if st.session_state.stop_requested:
#                 break
#             response = api_request(token["api_secret"], RequestType.GET_ALL_USERS, GetAllUsers(token["api_key"], "", "candidate", page, 100))
#             status_code_user, req_output_user = response.status_code, response.text
#             print(status_code_user)
#             data = json.loads(req_output_user)
#             nbProfile = data["total"]
#             users = data["users"]
            
#             for user in users : 
                
#                 if user["id"] not in allProfiles :
#                     start_treatment = time.time()
                    
#                     nb_treated += 1
#                     allProfiles.append(user["id"])
#                     response = api_request(token["api_secret"], RequestType.GET_USER_CV, GetUserCv(token["api_key"], "", user["id"]))
#                     status_code_cv, req_output_cv = response.status_code, response.text
#                     cv = json.loads(req_output_cv)
#                     date_str = "2000-01-01T01:01:01+01:00"
                    
#                     for item in cv  :
#                         ref = datetime.fromisoformat(date_str)
#                         cv_date = datetime.fromisoformat(item["updated"])
#                         if cv_date > ref :
#                             cv_id = item["id"]
#                     response = api_request(token["api_secret"], RequestType.EXPORT_CV, ExportCv(token["api_key"], "", cv_id))
#                     status_code_export, req_output_export = response.status_code, response.content
                    
#                     with open(f"{USER_DATA_DIR}\\CV_n_{cv_id}.docx", "wb") as f :
#                         print(str(f"{USER_DATA_DIR}\\CV_n_{cv_id}"))
#                         f.write(req_output_export)
#                     treatment_time = (treatment_time + time.time() - start_treatment)
#                     mean_treatmment_time = treatment_time / nb_treated
#                     remaining_time = mean_treatmment_time * (nbProfile - nb_treated)
#                     if remaining_time >= 60 :
#                         estimation_mn = str(int(remaining_time/60))+"mn"
#                     else : 
#                         estimation_mn = ""
#                     estimation_sec = str(int((remaining_time%60))) + "s"
#                     estimation = estimation_mn + estimation_sec
#                     progress_bar.progress((len(allProfiles)/nbProfile), text=f"Récupération des profils en cours. Temps restant estimé : {estimation}")
            
#             page += 1

#             timeout = nbProfile 
#             elapsed_time = time.time() - start_time
#             if elapsed_time > timeout :
#                 print("TIMEOUT !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
#                 break

#         progress_bar.empty()
#         if st.session_state.stop_requested:
#             st.session_state.stage = 0
#             st.session_state.stop_requested = False
#             st.info("Téléchargement interrompu par l'utilisateur")
#             return
#         if allProfiles != [] :
#             if len(allProfiles) != nbProfile :
#                 if elapsed_time > timeout :
#                     st.session_state.fetch_state = 3
#                 else :
#                     print(nbProfile)
#                     print(status_code_user)
#                     print(len(allProfiles))
#                     print(status_code_user)
#                     st.session_state.fetch_state = 2
#             toDisplay = ""
#             for manager in allProfiles :
#                 toDisplay = toDisplay + str(manager) + "\n"
#             st.text_area("Users", toDisplay )
#         else : 
#             st.session_state.fetch_state = 1

#         if st.session_state.fetch_state != 0 :
#             fetch_error_dialog()
#     return True

# def start_fetch() :
#     st.session_state.stop_requested = False
#     st.session_state.stage = 1
#     t = threading.Thread(target=fetch_profiles)
#     t.start()
#     st.session_state.worker_thread = t


# def fetch_profiles_worker(state) :
#     for user


# def start_job() :
#     reset_state()
#     launch_worker()
#     return True

# def ask_stop():
#     st.session_state.stop_requested = True

# def render() :
#     st.title("Gestion de la base de données")

#     if not is_running() :
#         st.button('Récupérer tous les profils', on_click=start_job)
#     else : 
#         st.button('Annuler', on_click=ask_stop)
   
#     return True
