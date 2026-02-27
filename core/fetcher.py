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
from core.database import init_db, start_writer, load_users_cv_dates, cv_raw_exists


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
    request_cv = 0
    start_time = time.time()
    failed_fetch = 0
    # récupérer les CV
    response = api_request(
        api_secret,
        RequestType.GET_USER_CV,
        GetUserCv(api_key, "", user["id"])
    )

    cvs = json.loads(response.text)

    latest_cv_id = None
    needs_parsing = 1
    doc_ok = 0
    cv_url = ""
    cv_completion = 0
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
        return start_time, "", 0

    latest_cv_date = None
    if not latest_cv_id or not cv_completion :
        needs_parsing = 0
        # try :
        #     writer_queue.put({"type": "upsert_user", "data": (user["id"],
        #                                                 user["firstname"],
        #                                                 user["lastname"],
        #                                                 user["username"])})
            
        #     writer_queue.put({"type": "upsert_cv", "data": (latest_cv_id,
        #                                                 user["id"],
        #                                                 latest_cv_date,
        #                                                 needs_parsing)})
        # except Exception as e :
        #     print(e)
        # return start_time

    else : 
        db_cv_date = existing_users.get(user["id"])
        latest_db_cv_date = 0
        if db_cv_date != None :
            latest_db_cv_date = datetime.fromisoformat(db_cv_date)

        if latest_date != latest_db_cv_date or not cv_raw_exists(latest_cv_id) and latest_date != datetime.fromisoformat("2000-01-01T01:01:01+01:00") :
            request_cv = latest_cv_id
            latest_cv_date = latest_date
            # response = api_request(
            #     api_secret,
            #     RequestType.EXPORT_CV,
            #     ExportCv(api_key, "", latest_cv_id)
            # )

            # if response.status_code == 200 :
            #     doc_ok = 1
            #     doc_bytes = response.content
            #     # writer_queue.put({"type": "upsert_cv_raw", "data": (latest_cv_id, doc_bytes)})
            #     needs_parsing = 1
            #     latest_cv_date = latest_date.isoformat()
            # else : 
            #     print("error fetching raw cv")
            #     print(user["id"])
            #     print(response)
            #     failed_fetch = user[id]
            #     latest_cv_id = None
            #     latest_cv_date = None
            #     needs_parsing = 0

        else : 
            print("else")
            print(latest_date)
            print(latest_db_cv_date)
            return start_time, "", 0

    try :
        # print("write user")
        writer_queue.put({"type": "upsert_user", "data": (user["id"],
                                                user["firstname"],
                                                user["lastname"],
                                                user["username"])})
        # print("write cv")
        writer_queue.put({"type": "upsert_cv", "data": (latest_cv_id,
                                                    user["id"],
                                                    latest_cv_date,
                                                    needs_parsing)})
        
        # if doc_ok == 1 :
        #     writer_queue.put({"type": "upsert_cv_raw", "data": (latest_cv_id, doc_bytes)})

    except Exception as e :
        print(e)

    # print("finished")

    return start_time, failed_fetch, request_cv


def download_cv_raw(cv_request, api_key, api_secret, writer_queue) : 
    print("downloading")
    start_time = time.time()
    response_doc = api_request(
        api_secret,
        RequestType.EXPORT_CV,
        ExportCv(api_key, "", cv_request, "doc")
    )

    response_pdf = api_request(
        api_secret,
        RequestType.EXPORT_CV,
        ExportCv(api_key, "", cv_request, "pdf")
    )
    
    print("reponses")
    if response_doc.status_code == 200 and response_pdf.status_code == 200 :
        doc_bytes = response_doc.content
        pdf_bytes = response_pdf.content
        writer_queue.put({"type": "upsert_cv_raw", "data": (cv_request, doc_bytes, pdf_bytes)})
    else : 
        print(response_doc.status_code)
        print(response_pdf.status_code)
        print("error fetching raw cv")
    
    print("download ended")
    return start_time

CV_REQUEST_LIST = ['3271792', '2271524', '1563888', '2930825', '2089604', '3735251', '1694333', '1650719', '1670498', '2190229', '3537478', '1684965', '1687928', '2794072', '1895077', '1699251', '1699633', '1782173', '4625720', '1799595', '2587752', '4146994', '1735945', '2509610', '2091733', '2595742', '1787915', '1798114', '2766785', '1770654', '1791382', '1771641', '1777288', '3021377', '1937208', '1797783', '2282087', '1980374', '1816358', '2439631', '1830229', '2089616', '1836445', '3702302', '1865067', '3595651', '2849859', '2148679', '2183065', '2021600', '2259100', '2390324', '4241731', '4603480', '2135649', '4268843', '2253770', '2038583', '3847100', '2155712', '2058181', '2064155', '3771796', '2074917', '2707105', '4627578', '2166083', '2110589', '2208587', '2298802', '2158042', '2188539', '2188844', '2570434', '2194743', '2839137', '2612478', '2229487', '2255513', '2247046', '4351797', '3832803', '4637413', '2275864', '2590187', '2371775', '2610435', '2434046', '2840395', '3930511', '2522251', '2724724', '2426645', '2689794', '2605655', '3036878', '2686181', '2475170', '2812990', '2573871', '2485953', '3653106', '2936844', '2908972', '3231357', '2506783', '2496922', '2505484', '2934855', '2524738', '2527839', '4268654', '2611676', '2543849', '2547980', '3279998', '2678335', '2555080', '2901414', '3250981', '2554815', '4041750', '2574050', '2573741', '2937618', '3635925', '2581199', '3835540', '3136598', '2725424', '3773403', '2600077', '2614552', '2604115', '3138874', '4632103', '2624222', '2626351', '3875904', '2631908', '3106011', '2665945', '2708317', '4269315', '2672489', '2674478', '2671556', '3867281', '3120192', '2677153', '4613936', '2922337', '2891512', '2876180', '2845322', '2689417', '2692156', '2815167', '2771814', '3157406', '2715361', '2787186', '2730801', '2732087', '2734685', '2745097', '2755031', '2916304', '4269251', '2769243', '2808670', '2797288', '2776173', '2776582', '2785093', '4281813', '2792517', '2791199', '2793047', '2848290', '3251960', '2795431', '4646702', '4270399', '4339775', '3410021', '3548339', '3225180', '2997690', '2845527', '2873754', '2847928', '2854933', '4389660', '2907355', '4039001', '3211807', '2866528', '2863841', '3063053', '2922312', '2880809', '2886792', '2884618', '2885095', '2888688', '2888734', '2892817', '3095446', '3064577', '3131015', '2907307', '3020528', '2917731', '4459273', '2944678', '4045030', '3482811', '2954504', '3188494', '3555529', '2961801', '3927483', '3820138', '4035091', '3124725', '4269323', '3000697', '3655816', '2988773', '3165187', '2995091', '3110668', '4642932', '4268754', '3013158', '3013022', '3927758', '3017580', '3255857', '3227820', '3187182', '3414559', '4635403', '3403509', '4150901', '3055438', '3693048', '3843938', '3094799', '3063251', '3404414', '3246793', '4474955', '3074422', '3348688', '3096807', '3093524', '3098625', '4261185', '3846833', '3252049', '4545978', '3504869', '3241629', '3138830', '3144472', '3355561', '3329829', '3284279', '3149383', '4268678', '3160210', '3160600', '4324403', '3174583', '3176200', '4269220', '3854585', '3340244', '3197983', '3199301', '3203125', '3204960', '3207785', '3215152', '3462780', '3216708', '3389367', '3219320', '4488034', '3368788', '4557945', '3237671', '4595032', '3502687', '3258236', '3260046', '3708514', '3538909', '3412517', '3333149', '3821279', '3911977', '3300533', '3299165', '3314289', '4485098', '3315580', '3361115', '4646074', '3620113', '3515172', '3740190', '3606163', '4344839', '3384912', '3381107', '3385154', '4268999', '4401214', '3414153', '3399949', '3415867', '3416061', '4382240', '3718327', '3428471', '3435717', '4029520', '4308041', '4594607', '3452097', '3807226', '3449871', '3528666', '3452948', '3465889', '3486189', '3480632', '3939345', '3487074', '3494076', '3494048', '3529079', '4128466', '3508096', '4039425', '4269191', '3849279', '3564148', '3529304', '3558054', '3631975', '3697611', '3565383', '3566147', '4611445', '4634388', '3752441', '3581508', '3591060', '3615028', '3606109', '3596789', '3614852', '3603884', '4203705', '4340820', '3697640', '4561980', '4269080', '3621874', '3862220', '3632288', '4332107', '4195910', '3643058', '3787473', '3652981', '3856463', '3652999', '4083896', '4016335', '3885348', '4603392', '3652994', '3655992', '3779355', '3683088', '3698134', '3696688', '3701143', '3715065', '3709990', '3780061', '3840150', '3723861', '3734648', '3773188', '3775138', '4181499', '3803410', '4269332', '3778109', '3775572', '3771824', '4384318', '4350244', '4451401', '4538056', '4268827', '3823256', '4216759', '3845928', '4463146', '3864293', '3862946', '3870838', '3863975', '4500591', '3924656', '3886865', '3885103', '4451463', '4310265', '3906702', '3918672', '3917261', '3920082', '3933469', '4173571', '4426582', '4322236', '4171354', '3964634', '3990190', '4382796', '4269335', '4068044', '4269007', '4024273', '4269173', '4452823', '4057962', '4249564', '4628262', '4066928', '4060149', '4072873', '4092509', '4409455', '4089336', '4093588', '4094503', '4136450', '4153540', '4148777', '4173600', '4176486', '4544550', '4173168', '4417511', '4213317', '4206762', '4262817', '4377133', '4217286', '4230907', '4241656', '4382993', '4254873', '4332970', '4247606', '4462259', '4514902', '4266224', '4451211', '4342032', '4320578', '4319157', '4333297', '4378217', '4334787', '4349126', '4544742', '4372529', '4372105', '4419575', '4357420', '4644516', '4371976', '4372417', '4388340', '4492984', '4399659', '4424220', '4424903', '4419336', '4432539', '4431362', '4430679', '4430920', '4431096', '4430702', '4432968', '4431282', '4435988']
def fetch_profiles_worker(pipelineManager, api_key, api_secret, existing_users, writer_queue, selection):
    try:
        pipelineManager.message = "Initialisation..."
        retry_list = []
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

        cv_request_list = []


        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(process_user, user, api_key, api_secret, existing_users, writer_queue, selection)
                for user in users
            ]

            for future in as_completed(futures):
                # if state._stop_event:
                #     state.message = "Arrêt demandé"
                #     break

                a, b, c = future.result()  # lève erreur si besoin
                start_time = a
                if c != "" and c != 0 :
                    cv_request_list.append(c)
                treated += 1
                elapsed_time = time.time() - start_time
                pipelineManager.progress = treated / total
                total_time = total_time + elapsed_time
                mean_treatmment_time = total_time / treated
                remaining_time = mean_treatmment_time/15 * (total - treated)
                if remaining_time >= 60 :
                    estimation_mn = str(int(remaining_time/60))+"mn"
                else : 
                    estimation_mn = ""
                estimation_sec = str(int((remaining_time%60))) + "s"
                estimation = estimation_mn + estimation_sec
                    
                pipelineManager.message = f"{treated}/{total} profils traités. Environ {estimation} restantes"
                # start_time = time.time()

    except Exception as e:
        pipelineManager.error = str(e)
        print(e)
    try : 
        treated = 0
        total = len(cv_request_list)
        start_time = time.time()
        total_time = 0


        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(download_cv_raw, cv_request, api_key, api_secret, writer_queue)
                for cv_request in cv_request_list
            ]

            for future in as_completed(futures):
                # if state._stop_event:
                #     state.message = "Arrêt demandé"
                #     break

                start_time = future.result()  # lève erreur si besoin
                treated += 1
                elapsed_time = time.time() - start_time
                pipelineManager.progress = treated / total
                total_time = total_time + elapsed_time
                mean_treatmment_time = total_time / treated
                remaining_time = mean_treatmment_time/8 * (total - treated)
                if remaining_time >= 60 :
                    estimation_mn = str(int(remaining_time/60))+"mn"
                else : 
                    estimation_mn = ""
                estimation_sec = str(int((remaining_time%60))) + "s"
                estimation = estimation_mn + estimation_sec
                print(estimation)
                    
                pipelineManager.message = f"{treated}/{total} profils traités. Environ {estimation} restantes"
                # start_time = time.time()

        
    except Exception as e :
        print(e)

    finally :
        print(("finally fetcher"))
        

        print(cv_request_list)
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
