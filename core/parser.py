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


@dataclass
class Experience :
    title     : str
    company   : str
    duration  : str
    details   : list


Heading_dict_type_1 = {
    "Heading 2" : "title",
    "Heading 5" : "company",
    "Heading 6" : "duration", 
    "details"   : "Heading 4"
}

Heading_dict_type_2 = {
    "Heading 2" : "title",
    "Heading 6" : "company",
    "Heading 7" : "duration",
    "details"   : "Heading 5"
}

Heading_dict_type_3 = {
    "Heading 3" : "title",
    "Heading 7" : "company",
    "Heading 8" : "duration",
    "details"   : "Heading 6"
}


def get_details(paragraphs, index, heading_dict, exp_details : Experience) :
    while index < len(paragraphs) :
        para = paragraphs[index]
        para_style = para.style.name
        if heading_dict == Heading_dict_type_1 and "Heading 4" in para_style  :
            index += 1
        elif "Heading" in para_style : 
            break
        else : 
            if para.text != "" and not re.search("\\d / \\d", para.text) :
                exp_details.details[-1].append(para.text.strip("+ \t"))
            index += 1
    return index


def parse_exp_details(paragraphs, index, heading_dict, exp_details : Experience) :
    while index < len(paragraphs) :
        para = paragraphs[index]
        para_style = para.style.name
        if para_style in heading_dict :
            if heading_dict[para_style] == "title" :
                break
            elif heading_dict[para_style] == "company" :
                exp_details.company = para.text
            elif heading_dict[para_style] == "duration" :
                exp_details.duration = para.text
            index += 1
        elif heading_dict["details"] in para_style :
            exp_details.details.append([para.text])
            new_index = get_details(paragraphs, index + 1, heading_dict, exp_details)
            index = new_index
        else :
            index += 1


def parse_skills(paragraphs, index) :
    skills = []
    while index < len(paragraphs) :
        para = paragraphs[index]
        para_style = para.style.name
        if "Heading 1" in para_style :
            break
        else :
            if "Heading" not in para.style.name and para.text != "" :
                skills.append(para.text.strip("+ \t"))
        index += 1
    return skills

                
def parse_cv(file) :
    doc = docx.Document(io.BytesIO(file))
    reading_exp = -1
    reading_skills = -1
    heading_dict = Heading_dict_type_1
    experiences = []
    skills = []
    for index, p in enumerate(doc.paragraphs) :
        if "Heading 4" in p.style.name and p.text == "THINK2MORROW" :
            heading_dict = Heading_dict_type_2
            break
        elif "Heading 5" in p.style.name and p.text == "THINK2MORROW" :
            heading_dict = Heading_dict_type_3
            break
    for index, p in enumerate(doc.paragraphs) :
        if reading_exp == 0 and p.style.name in heading_dict and heading_dict[p.style.name] == "title":
            exp_details = Experience(p.text, "", "", [])
            parse_exp_details(doc.paragraphs, index + 1, heading_dict, exp_details)
            exp_dict = asdict(exp_details)
            experiences.append(exp_details)

        if "Heading 1" in p.style.name and "experiences" == unidecode(p.text.lower()) : 
            reading_exp = 0
            continue

        if "Heading 1" in p.style.name and ("competences" in unidecode(p.text.lower()) or "skills" in unidecode(p.text.lower())) : 
            skills = parse_skills(doc.paragraphs, index + 1)
            continue
                
        if reading_exp == 0 and "Heading 1" in p.style.name :
            reading_exp = 1

        if reading_skills == 0 and "Heading 1" in p.style.name :
            reading_skills = 1

        if reading_exp == 1 and reading_skills == 1 :
            break

    exp_json = json.dumps(experiences)
    skills_json = json.dumps(skills)
    print(experiences)
    return exp_json, skills_json


def parse_worker(pipelineManager, selection, writer_queue):
    treated = 0
    total = get_total_cv_parsing()

    print(total)

    for cv_id, cv_raw in read_raw_data():
        try :
            # if pipelineManager._stop_event :
            #     break
            print('!!!!!!!')
            exp, skills = parse_cv(cv_raw)
            treated += 1
            pipelineManager.progress = treated / total      
            pipelineManager.message = f"{treated}/{total} profils traités"
            if skills == [] :
                print(cv_id)
            writer_queue.put({"type": "upsert_cv_parsed", "data": (cv_id, exp, skills)})
        except Exception as e :
            print(e)

    
    pipelineManager.step += 1


def start_parse(pipelineManager, stop_event):
    init_db()
    existing_users = load_users_cv_dates()
    writer_queue, stop_event, writer_thread = start_writer()
    parse_worker(pipelineManager, stop_event, writer_queue)
