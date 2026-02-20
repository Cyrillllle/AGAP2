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

from api.client import api_request, RequestType, GetAllUsers, GetUserCv, ExportCv
from core.storage import USER_DATA_DIR, TOKEN_PATH
from core.database import *
from core.parser import *


def get_ngrams(token, n) :
    if len(token) > 1 :
        return [" ".join(token[i:i+n]) for i in range(len(token)-n+1)]
    else :
        return token


delimiters = [" ", ",", ":", "/", "(", ")"]

# def searching(searched) :
#     all = []
#     for cv_id, exp, skills in read_parsed_data() :
#         experience = json.loads(exp)
#         # print(cv_id)
#         for ex in experience :
#             title = ex["title"]
#             details = ex["details"]
#             company = ex["company"]
#             # if company != "" :
#             #     if unidecode(searched.lower()) in unidecode(company.lower()) :
#             #         print(title)
#             #         print(company)

#             # if unidecode(searched.lower()) in unidecode(title.lower()) :
#             #     print(title)
#             #     print(company)


#             if len(details) != 0 :
#                 for det in details :
#                     if len(det) != 0 :
#                         if "techni" in det[0].lower() :
#                             # for func in searched :
#                             search = unidecode(searched.lower())
#                             # if match.extract(search, det, score_cutoff=0.4, limit=2) != [] :
#                             #     print(match.extract(search, det, score_cutoff=0.4, limit=2))
#                             #     print(cv_id)


#                             for d in det :
#                                 for _ in delimiters :
#                                     if _ in d :
#                                         d = d.replace(_, ";")
#                                 tokens = d.split(";")
#                                 for token in tokens :
#                                     if token != "" and token not in all_token :
#                                         all_token.append(token)
#                                 if len(search.split(" ")) == 1 :
#                                     for token in tokens :
#                                         if search == unidecode(token.lower()) :
#                                             if cv_id not in all :
#                                                 all.append(cv_id)
#                                             # print(cv_id)
#                                             # print(token)
#                                             break
#                                 elif len(search.split(" ")) == 2 :
#                                     bigrams = ngrams(tokens, 2)
#                                     for bigram in bigrams :
#                                         if search == unidecode(bigram.lower()) :
#                                             print(bigram)
#                                             print(cv_id)
#                                             if cv_id not in all :
#                                                 all.append(cv_id)
#                                             break
#                                 elif len(search.split(" ")) == 3 :
#                                     trigrams = ngrams(tokens, 3)
#                                     for trigram in trigrams :
#                                         if search == unidecode(trigram.lower()) :
#                                             print(trigram)
#                                             print(cv_id)
#                                             if cv_id not in all :
#                                                 all.append(cv_id)
#                                             break
#     return all

# A = searching("finops")
# print(A)

def search_skills(skills, tokens) :
    all = []
    try :
        for category in skills :
            for skill in skills[category] :
                ngrams = get_ngrams(tokens, len(skill.split(" ")))
                for ngram in ngrams :
                    if unidecode(skill.lower()) == unidecode(ngram.lower()) :
                        all.append(skill)
                        # print(cv_id)
                        # print(token)
                        break
    except Exception as e:
        print(e)
        print(skill)
        print(ngrams)
    return all

def analyze_cv(cv_parsed, cv_id, skills) :
    all = []
    experiences = json.loads(cv_parsed)
    for exp in experiences :
        title = exp["title"]
        details = exp["details"]
        company = exp["company"]
        if len(details) != 0 :
            for detail in details :
                if len(detail) > 1 and "techni" in detail[0].lower() :
                    for d in detail[1:] :
                        for _ in delimiters :
                            if _ in d :
                                d = d.replace(_, ";")
                        tokens = d.split(";")
                        if len(tokens) > 0 :
                            all += search_skills(skills, tokens)
    print(all)
    return all

def analyze_worker(pipelineManager, selection, writer_queue, skills):
    treated = 0
    total = get_total_cv_parsing()
    total_time = 0
    cpt = 0
    all = []

    for cv_id, experiences, raw_skills in read_parsed_data():
        # try :
            # if pipelineManager._stop_event :
            #     break
        start_time = time.time()
        all = analyze_cv(experiences, cv_id, skills)
        if all == [] :
            print(cv_id)
            cpt += 1
        elapsed_time = time.time() - start_time
        treated += 1
        total_time = total_time + elapsed_time
        mean_treatmment_time = total_time / treated
        remaining_time = mean_treatmment_time * (total - treated)
        if remaining_time >= 60 :
            estimation_mn = str(int(remaining_time/60))+"mn"
        else : 
            estimation_mn = ""
        estimation_sec = str(int((remaining_time%60))) + "s"
        estimation = estimation_mn + estimation_sec
        
        pipelineManager.progress = treated / total      
        pipelineManager.message = f"{treated}/{total} profils traités. Environ {estimation} restantes"

            # writer_queue.put({"type": "upsert_cv_parsed", "data": (cv_id, exp, skills)})
        # except Exception as e :
        #     print(e)

    print(cpt)
    pipelineManager.step += 1


def start_analyze(pipelineManager, stop_event):
    init_db()
    existing_users = load_users_cv_dates()
    file = open(SKILLS_PATH)
    skills = json.load(file)
    file.close()
    writer_queue, stop_event, writer_thread = start_writer()
    analyze_worker(pipelineManager, stop_event, writer_queue, skills)
