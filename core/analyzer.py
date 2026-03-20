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
from core.skills import update_skills_db


@dataclass
class Exp_skill :
    skill : str
    duration : int

months_num_fr = {   1: 'Janvier',
                    2: 'Février',
                    3: 'Mars',
                    4: 'Avril',
                    5: 'Mai',
                    6: 'Juin',
                    7: 'Juillet',
                    8: 'Août',
                    9: 'Septembre',
                    10: 'Octobre',
                    11: 'Novembre',
                    12: 'Décembre'}

months_num_en = {   1: 'January',
                    2: 'February',
                    3: 'March',
                    4: 'April',
                    5: 'May',
                    6: 'June',
                    7: 'July',
                    8: 'August',
                    9: 'September',
                    10: 'October',
                    11: 'November',
                    12: 'December'}



def get_ngrams(token, n) :
    if len(token) > 1 :
        return [" ".join(token[i:i+n]) for i in range(len(token)-n+1)]
    else :
        return token


delimiters = [" ", ",", ":", "/", "(", ")"]


def search_skills(skills, tokens) :
    all = []
    try :
        for skill_id in skills :
            skill =skills[skill_id]
            ngrams = get_ngrams(tokens, len(skill.split(" ")))
            for ngram in ngrams :
                if unidecode(skill.lower()) == unidecode(ngram.lower()) :
                    all.append(skill_id)
                    break
    except Exception as e:
        print(e)
        print(skill)
        print(ngrams)
    return all


def get_nb_months(duration) :
    try :
        posStart = 0
        posMiddle = 0
        if "à" in duration :
            months_num = months_num_fr
            posMiddle = duration.find("à")
            durationType = "closed"
        elif "to" in duration :
            months_num = months_num_en
            posMiddle = duration.find("to")
            durationType = "closed"
        elif "depuis" in unidecode(duration.lower()) :
            months_num = months_num_fr
            posStart = duration.find("depuis")
            durationType = "opened"
        elif "since" in unidecode(duration.lower()) :
            months_num = months_num_en
            posStart = duration.find("since")
            durationType = "opened"

        if durationType == "closed" :
            start = unidecode(duration[:posMiddle].lower())
            end = unidecode(duration[posMiddle:].lower())
        elif durationType == "opened" :
            start = unidecode(duration[posStart:].lower())
            end = ""
        for num in months_num :
            if unidecode(months_num[num].lower()) in start :
                start_month = num
                start_year =  re.search(r"(\d{4})", start).group(1)
            if unidecode(months_num[num].lower()) in end :
                end_month = num
                end_year =  re.search(r"(\d{4})", end).group(1)

        start_date = datetime.strptime(f"{str(start_year)}-{str(start_month)}-01", '%Y-%m-%d').date()
        if durationType == "closed" :
            end_date = datetime.strptime(f"{str(end_year)}-{str(end_month)}-28", '%Y-%m-%d').date() 
        elif durationType == "opened" :
            end_date = datetime.today().date()

        nb_months = round((end_date - start_date).days/30.44)
    
    except Exception as e :
        nb_months = -1
    
    if nb_months < 0 :
        nb_months = -1

    return nb_months


def analyze_cv(cv_parsed, cv_id, skills) :
    print("analyse")
    all = []
    experiences = json.loads(cv_parsed)
    all_skills_exp = 0
    for exp in experiences :
        exp_skills = []
        nb_months = -1
        title = exp["title"]
        details = exp["details"]
        company = exp["company"]
        duration = exp["duration"]
        nb_months = get_nb_months(duration)
        all_skills_exp += nb_months
        if len(details) != 0 :
            for detail in details :
                if len(detail) > 1 and "techni" in detail[0].lower() :
                    for d in detail[1:] :
                        for _ in delimiters :
                            if _ in d :
                                d = d.replace(_, ";")
                        tokens = d.split(";")
                        if len(tokens) > 0 :
                            exp_skills += search_skills(skills, tokens)
        if len(exp_skills) > 0 :
            for skill in exp_skills :
                added = False
                for o_skill in all :
                    if o_skill.skill == skill :
                        added = True
                        if nb_months != -1 :
                            o_skill.duration += nb_months
                        break
                if added == False :
                    all.append(Exp_skill(skill, nb_months))
            all.append(Exp_skill("ALL_SKILLS_EXP", all_skills_exp))
    return all

def analyze_worker(pipelineManager, selection, writer_queue, skills):
    treated = 0
    total = get_total_cv_parsing()
    total_time = 0
    cpt = 0
    all = []
    for cv_id, experiences, raw_skills in read_parsed_data():        

        start_time = time.time()
        all = analyze_cv(experiences, cv_id, skills)
        if all == [] :
            # print(cv_id)
            cpt += 1
        else :
            for exp_skill in all :
                if exp_skill.skill != "ALL_SKILLS_EXP" :
                    writer_queue.put({"type": "upsert_cv_skill", "data": (cv_id, exp_skill.skill, exp_skill.duration)})
                else : 
                    writer_queue.put({"type": "upsert_cv_total_exp", "data": (exp_skill.duration, cv_id)})
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

    pipelineManager.step += 1


def start_analyze(pipelineManager, stop_event):
    init_db()
    temp()
    # update_skills_db()
    existing_users = load_users_cv_dates()
    update_skills_db()
    skills = read_skills_by_id()
    writer_queue, stop_event, writer_thread = start_writer()
    print("la")
    analyze_worker(pipelineManager, stop_event, writer_queue, skills)
