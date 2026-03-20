import streamlit as st
from api import client
from core.storage import init_storage
from ui.pages import init, fetch, show, search, apiToken, anaParse, pipeline, skills, jobs
from pathlib import Path
import pandas as pd



st.set_page_config(layout="wide")
st.html("<style>[data-testid='stHeaderActionElements'] {display: none;}</style>")

init_storage()

INIT_PAGES = {
    "init": init.render,
    "token": apiToken.render,
    "token_input": apiToken.token_get, 
    # "detail": detail.render,
}

@st.dialog("Attention")
def leaving_page(current_page) :
    leaving_confirm = False
    st.write("Les modifications non sauvegardées seront perdues")
    col1, col2 = st.columns([1,1])
    with col2 :
        if st.button("Confirmer", width="stretch"):
            leaving_confirm = True
    with col1 : 
        if st.button("Annuler", width="stretch") :
            st.switch_page(current_page)
            st.rerun()

if "error_count" not in st.session_state:
    st.session_state.error_count = 0


# état initial
if "current_page" not in st.session_state:
    st.session_state.current_page = "init"
if "previous_page" not in st.session_state : 
    st.session_state.previous_page = ""


if "skills_modified" not in st.session_state :
    st.session_state.skills_modified = []
if "available_skills" not in st.session_state :
    st.session_state.available_skills = []
if "selected_skills" not in st.session_state :
    st.session_state.selected_skills = pd.DataFrame({"skills": [None]}, index=[0])



# else : 
#     st.sidebar.title("Navigation")
#     selection = st.sidebar.radio("Aller à", list(PAGES.keys()))
#     PAGES[selection]()

try : 

    pages = {
        "Gestion de la base de données": [
            st.Page("ui/pages/pipeline.py", title="Mettre à jour la base de données"),
            # st.Page("manage_account.py", title="Manage your account"),
        ],
        "Compétences": [
            st.Page("ui/pages/jobs.py", title="Fiches métiers"),
            st.Page("ui/pages/skills.py", title="Liste des compétences"),
            # st.Page("trial.py", title="Try it out"),
        ],
        "Recherche": [
            st.Page("ui/pages/search.py", title="Recherche par métier"),
            # st.Page("ui/pages/search.py", title="Recherche par nom"),
            # st.Page("trial.py", title="Try it out"),
        ],
    }

    future_page = ""
    if st.session_state.current_page == "init" or st.session_state.current_page == "token" or st.session_state.current_page == "token_input" :
        INIT_PAGES[st.session_state.current_page]()
    else :
        st.session_state.previous_page = st.session_state.current_page
        future_page = st.navigation(pages, position="sidebar")
        if st.session_state.previous_page.title == "Liste des compétences" and len(st.session_state.skills_modified) != 0 and future_page.title != "Liste des compétences" : 
            if st.session_state.skills_saved == True :
                print("fichier sauvegardé")
            else :
                leaving_confirm = leaving_page(st.session_state.previous_page)
                future_page = st.session_state.current_page
                print("attention fichier non sauvegardé")
        elif st.session_state.previous_page.title == "Fiches métiers" and st.session_state.jobs_modified and future_page.title != "Fiches métiers" : 
            if st.session_state.skills_saved == True :
                print("fichier sauvegardé")
            else :
                leaving_confirm = leaving_page(st.session_state.previous_page)
                future_page = st.session_state.current_page
                print("attention fichier non sauvegardé")
        else :
            st.session_state.current_page = future_page
            # st.session_state.skills_modified = []
            st.session_state.current_page.run()

except Exception as e :
    st.session_state.error_count += 1

    if st.session_state.error_count <= 2:
        st.rerun()

    else:
        st.session_state.error_count = 0
        st.error(f"Erreur persistante : {e}")
        if st.button("Réessayer"):
            st.rerun()