import pandas as pd
import streamlit as st
from pathlib import Path
import json
from unidecode import unidecode
import copy

from core.database import *
from core.paths import *
from core.storage import *


if "init_skills" not in st.session_state :
    st.session_state.init_skills = True

if "available_skills" not in st.session_state :
    st.session_state.available_skills = []

if "displayed_skills" not in st.session_state :
    st.session_state.displayed_skills = ""

if "db_skills" not in st.session_state :
    st.session_state.db_skills = ""

if "skills_data" not in st.session_state :
    st.session_state.skills_data = ""

if "temp_skills_data" not in st.session_state :
    st.session_state.temp_skills_data = {}

if "skills_modified" not in st.session_state :
    st.session_state.skills_modified = []

if "skills_saved" not in st.session_state :
    st.session_state.skills_saved = False

@st.dialog("Attention")
def confirm_delete(jobs_data, job_name) :
    st.write("Confirmer la suppression de la fiche métier ?")
    col1, col2 = st.columns([1,1])
    with col2 :
        if st.button("Confirmer", width="stretch"):
            jobs_data.pop(job_name)
            save_skills(jobs_data)
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
                save_skills(jobs_data)
                st.rerun()
            else :
                already_exists_error = True 
                
    with col1 : 
        if st.button("Annuler", width="stretch") :
            return False
    
    if already_exists_error == True :
        st.error("Le nom entré existe déjà")


def update_data(skills_data, editor_data) :
    data_copy = copy.deepcopy(skills_data)
    # category = category.lower()
    if editor_data["edited_rows"] != [] :
        edited = editor_data["edited_rows"]
        for edited_index in edited :
            if edited[edited_index] != {} :
                if edited[edited_index]["Compétences"] == "" :
                    data_copy.pop(edited_index)
                else : 
                    data_copy[edited_index] = edited[edited_index]["Compétences"]
    if editor_data["added_rows"] != [] :
        for added in editor_data["added_rows"] :
            if added != {} :
                data_copy.append(added["Compétences"])
    if editor_data["deleted_rows"] != [] :
        for deleted in editor_data["deleted_rows"] :
            data_copy.pop(deleted)
    return data_copy



def load_skills():
    if not SKILLS_PATH.exists():
        return {}
    with open(SKILLS_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    with open(SKILLS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_skills(data):
    with open(SKILLS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    st.session_state.skills_saved = True
    st.session_state.skills_modified = []

st.title("Gestion des compétences métiers")


if st.session_state.skills_saved == True :
    st.toast("Modifications sauvegardées !")
    st.session_state.skills_saved = False

print(st.session_state.skills_modified)
if len(st.session_state.skills_modified) == 0 :
    print("loading skills")
    st.session_state.skills_data = load_skills()
    # st.session_state.temp_skills_data = st.session_state.skills_data
# else : 
#     st.session_state.skills_data = st.session_state.temp_skills_data.copy()
#     print(st.session_state.skills_modified)

if not st.session_state.skills_data:
    st.warning("Aucun fichier skills.json trouvé. Création d'un nouveau.")
    st.session_state.skills_data = {"languages": [], "frameworks": [], "methodologies": [], "tools": []}

tab_list = []
for cat in st.session_state.skills_data :
    tab_list.append(cat.capitalize())

tab_obj = st.tabs(tab_list, on_change="rerun")

current_tab_index = -1
for index, tab in enumerate(tab_obj) :
    tab_name = tab_list[index]
    with tab :
        if index in st.session_state.skills_modified :
            skills_list = st.session_state.temp_skills_data[tab_list[index].lower()] 
        else : 
            skills_list = st.session_state.skills_data[tab_list[index].lower()] 

        edited = st.data_editor(
            [{"Compétences": s} for s in skills_list], 
            num_rows="dynamic",
            key=f"editor_{tab_name}",
        )
        
    if tab.open :
        st.session_state.displayed_skills = tab_list[index]
        current_tab_index = index


    if index not in st.session_state.skills_modified :
        st.session_state.temp_skills_data[tab_name.lower()] = update_data(st.session_state.skills_data[tab_name.lower()], st.session_state[f"editor_{tab_name}"])
        if st.session_state.temp_skills_data[tab_name.lower()] != st.session_state.skills_data[tab_name.lower()] :
            st.session_state.skills_modified.append(index)
        else : 
            if index in st.session_state.skills_modified :
                st.session_state.skills_modified.remove(index)

print(st.session_state.skills_modified)
                                  
col1, col2, col3 = st.columns([1,1,3])
with col1 :
    save_button = st.button("Sauvegarder", disabled=current_tab_index not in st.session_state.skills_modified, width="stretch")
with col2 :
    save_all_button = st.button("Tout sauvegarder", disabled=len(st.session_state.skills_modified)==0, width="stretch")


if save_button :
    # print(st.session_state[f"editor_{st.session_state.displayed_skills}"])
    st.session_state.skills_data[st.session_state.displayed_skills.lower()] = copy.deepcopy(st.session_state.temp_skills_data[st.session_state.displayed_skills.lower()])
    save_skills(st.session_state.skills_data)
    st.rerun()


if save_all_button :
    # for tab_name in tab_list :
    #     st.session_state.skills_data = update_data(st.session_state.skills_data, tab_name, st.session_state[f"editor_{tab_name}"])
    st.session_state.skills_data = copy.deepcopy(st.session_state.temp_skills_data)
    save_skills(st.session_state.temp_skills_data)
    st.rerun()