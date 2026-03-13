import pandas as pd
import streamlit as st
from pathlib import Path
import json
from unidecode import unidecode

from core.database import *
from core.paths import *
from core.storage import *


if "init_jobs" not in st.session_state :
    st.session_state.init_jobs = True

if "available_skills" not in st.session_state :
    st.session_state.available_skills = []

if "displayed_job" not in st.session_state :
    st.session_state.displayed_job = ""

if "db_skills" not in st.session_state :
    st.session_state.db_skills = ""

if "jobs_data" not in st.session_state :
    st.session_state.jobs_data = ""


@st.dialog("Attention")
def confirm_delete(jobs_data, job_name) :
    st.write("Confirmer la suppression de la fiche métier ?")
    col1, col2 = st.columns([1,1])
    with col2 :
        if st.button("Confirmer", width="stretch"):
            jobs_data.pop(job_name)
            save_jobs(jobs_data)
            st.rerun()
    with col1 : 
        if st.button("Annuler", width="stretch") :
            st.rerun()

@st.dialog("Nouvelle fiche métier")
def input_job_creation(jobs_data) :
    already_exists_error = False
    new_job_name = st.text_input("Entrer le nom de la fiche à créer")
    col1, col2 = st.columns([1,1])
    with col2 :
        if st.button("Confirmer", width="stretch", disabled=not new_job_name):
            if new_job_name not in jobs_data :
                jobs_data[new_job_name] = {
                    "required" : [[]], 
                    "optional" : [[]]
                }
                save_jobs(jobs_data)
                st.rerun()
            else :
                already_exists_error = True 
                
    with col1 : 
        if st.button("Annuler", width="stretch") :
            return False
    
    if already_exists_error == True :
        st.error("Le nom entré existe déjà")


def update_data(jobs_data, job_name, required, optional) :
    required_lists = required["required"].tolist()
    if required_lists != [] :
        jobs_data[job_name]["required"] = required_lists
    optional_lists = optional["optional"].tolist()
    if optional_lists != [] :
        jobs_data[job_name]["optional"] = optional_lists



def load_jobs():
    if not JOB_PATH.exists():
        return {}
    with open(JOB_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        print("CONTENT:", repr(content))
    with open(JOB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_jobs(data):
    with open(JOB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


cat_colors = {
    "languages" : "#9f2e2e", 
    "frameworks" : "#3359a3", 
    "methods" : "#3b9b4a", 
    "tools" : "#c2bc50"
}


def init_skills(skills) :
    db_skills = read_skills_by_cat()
    for cat in db_skills :
        for skill in db_skills[cat] :
            skills.append(skill)    

def get_color(skill, db_skills) :
    color = "grey"
    for cat in db_skills :
        for db_skill in db_skills[cat] :
            if db_skill == skill :
                color = cat_colors[cat]
                break
    return color

def set_displayed_job(job) :
    st.session_state.displayed_job = job

# def render(): 

if st.session_state.init_jobs == True :
    st.session_state.db_skills = read_skills_by_cat()
    st.session_state.jobs_data = load_jobs()


st.title("Gestion des fiches métiers")
st.space("small")



col1, col2, col3 = st.columns([0.9, 0.1, 3])
    

skills = []
colors = []

if st.session_state.available_skills == [] :
    print("here")
    init_skills(st.session_state.available_skills)



with col1 :
    st.space("xsmall")
    # new_category = st.text_input("Nom du métier")
    for job in st.session_state.jobs_data :
        print(job)
        st.button(job, on_click=set_displayed_job, args=[job], width="stretch")

    st.markdown("___")
    create_button = st.button("Créer fiche métier", width="stretch")

if create_button :
    input_job_creation(st.session_state.jobs_data)

with col2 :
    st.html(
        '''
            <div class="divider-vertical-line"></div>
            <style>
                .divider-vertical-line {
                    border-left: 2px solid rgba(49, 51, 63, 0.2);
                    height: 320px;
                    margin: auto;
                }
            </style>
        '''
    )

with col3 :
    st.space("xsmall")
    if st.session_state.displayed_job != "" :
        rows = []
        job = st.session_state.jobs_data[st.session_state.displayed_job]
        for or_list in job["required"]:
            row = []
            for skill in or_list :
                for a_skill in st.session_state.available_skills :
                    if unidecode(skill.lower()) == a_skill :
                        row.append(a_skill)
            rows.append(row)
        required_df = pd.DataFrame({"required" : rows})
        rows = []
        for or_list in job["optional"]:
            row = []
            for skill in or_list :
                for a_skill in st.session_state.available_skills :
                    if unidecode(skill.lower()) == a_skill :
                        row.append(a_skill)
            rows.append(row)
        optional_df = pd.DataFrame({"optional" : rows})

        st.markdown("Compétences obligatoires")
        required_editor = st.data_editor(
            required_df, num_rows="dynamic", key=f"required_{st.session_state.displayed_job}",
            column_config={
                "required": st.column_config.MultiselectColumn(
                    "App Categories",
                    help="The categories of the app",
                    color=[get_color(skill, st.session_state.db_skills) for skill in st.session_state.available_skills],
                    options=st.session_state.available_skills,
                    format_func=lambda x: x.capitalize(),
                ),
            },
        )

        st.markdown("Compétences optionnelles")

        optional_editor = st.data_editor(
            optional_df, num_rows="dynamic", key=f"optional_{st.session_state.displayed_job}",
            column_config={
                "optional": st.column_config.MultiselectColumn(
                    "App Categories",
                    help="The categories of the app",
                    color=[get_color(skill, st.session_state.db_skills) for skill in st.session_state.available_skills],
                    options=st.session_state.available_skills,
                    format_func=lambda x: x.capitalize(),
                ),
            },
        )

        col21, col22 = st.columns([0.5,0.5])
        with col21 :
            save_button = st.button("Sauvegarder", width="stretch")
    
        with col22:
            delete_button = st.button("Supprimer", width="stretch", key="delete_btn", type="primary")
            if delete_button:
                deletion = confirm_delete(st.session_state.jobs_data, st.session_state.displayed_job)
                if deletion != False : 
                    st.session_state.displayed_job = ""

        if save_button :
            update_data(st.session_state.jobs_data, st.session_state.displayed_job, required_editor, optional_editor)
            save_jobs(st.session_state.jobs_data)
            st.toast("Modifications sauvegardées !")

            
   

# tab_list = []
# for i in st.session_state.jobs_data :
#     tab_list.append(i)

# tab_obj = st.tabs(tab_list)

# for tab in tab_obj :
#     print(tab)