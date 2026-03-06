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
    colors = []
    db_skills = read_skills_by_cat()
    for cat in db_skills :
        for skill in db_skills[cat] :
            skills.append(skill)
            colors.append(cat_colors[cat])
    return colors, db_skills
    

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


col1, col2 = st.columns([1,3])
    

skills = []
colors = []

if st.session_state.available_skills == [] :
    print("here")
    init_skills(st.session_state.available_skills)




with col1 :
    new_category = st.text_input("Nom du métier")
    for job in st.session_state.jobs_data :
        print(job)
        st.button(job, on_click=set_displayed_job, args=[job])
    # if st.sidebar.button("Ajouter un nouveau métier"):
    #     if new_category and new_category not in st.session_state.jobs_data:
    #         st.session_state.jobs_data[new_category] = []
    #         save_jobs(st.session_state.jobs_data)
    #         st.rerun()


with col2 :
    if st.session_state.displayed_job != "" :
        rows = []
        job = st.session_state.jobs_data[st.session_state.displayed_job]
        for group in job["required"]:
            for skill in group.get("one_of", []) :
                print(skill)
                for a_skill in st.session_state.available_skills :
                    if unidecode(skill.lower()) == a_skill :
                        rows.append(a_skill)
            # for skill in group.get("all_of", []):
            
        data_df = pd.DataFrame({"category" : rows})

        testing = st.data_editor(
            data_df, num_rows="dynamic",
            column_config={
                "category": st.column_config.MultiselectColumn(
                    "App Categories",
                    help="The categories of the app",
                    color=[get_color(skill, st.session_state.db_skills) for skill in st.session_state.available_skills],
                    options=st.session_state.available_skills,
                    format_func=lambda x: x.capitalize(),
                ),
            },
        )

        # for category in st.session_state.jobs_data:

        #     st.subheader(f" {category}")

        #     jobs_list = st.session_state.jobs_data[category]

        #     # Ajouter un job
        #     col1, col2 = st.columns([3, 1])
        #     new_job = col1.text_input(f"Ajouter un job à {category}", key=f"add_{category}")

        #     col2.space("small")

        #     if col2.button("Ajouter", key=f"btn_{category}"):
        #         if new_job and new_job.lower() not in jobs_list:
        #             st.session_state.jobs_data[category].append(new_job.lower())
        #             save_jobs(st.session_state.jobs_data)
        #             st.rerun()

        #     # Edition tableau
        #     edited = st.data_editor(
        #         [{"job": s} for s in jobs_list],
        #         num_rows="delete",
        #         key=f"editor_{category}",
        #         width='stretch', 
        #     )

        #     # Mise à jour
        #     updated_list = [row["job"].lower() for row in edited if row["job"].strip() != ""]

        #     if updated_list != jobs_list:
        #         st.session_state.jobs_data[category] = sorted(list(set(updated_list)))
        #         save_jobs(st.session_state.jobs_data)
        #         st.success(f"{category} mis à jour !")


        # -------------------------
        # Sauvegarde manuelle
        # -------------------------

        if st.button("Sauvegarder tout"):
            save_jobs(st.session_state.jobs_data)
            st.success("Fichier sauvegardé !")

    # if not jobs_data:
    #     st.warning("Aucun fichier jobs.json trouvé. Création d'un nouveau.")
    #     jobs_data = {"languages": [], "frameworks": [], "methodologies": [], "tools": []}




    # last_selected_skills = st.session_state.selected_skills
    # st.session_state.selected_skills = st.data_editor(
    #     st.session_state.selected_skills, num_rows="dynamic",
    #     column_config={
    #     "skills": st.column_config.MultiselectColumn(
    #         "App Categories",
    #         help="The categories of the app",
    #         options=st.session_state.stable_available_skills,
    #         format_func=lambda x: x.capitalize(),
    #         ),
    #     },
    # )


    # if not st.session_state.selected_skills.equals(last_selected_skills) :
    #     print("heeeeeeeeeeeeeeeeeere")

    # print(st.session_state.available_skills)
    # if not st.session_state.selected_skills["skills"].empty :
    #     for row in st.session_state.selected_skills["skills"].tolist() :
    #         if row != None :
    #             for skill in row : 
    #                 print(str(skill))
    #                 if skill in st.session_state.available_skills :
    #                     print(True)
    #                 else : 
    #                     print(False)
                    # st.session_state.available_skills.remove(str(skill))

    # for a_skill in st.session_state.available_skills :
    #     if a_skill in st.session_state.selected_skills :
            

# print(st.session_state.selected_skills)

