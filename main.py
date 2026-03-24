import streamlit as st
import threading
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
}

# ✅ Défini avant les dialogs pour être accessible partout
pages = {
    "Gestion de la base de données": [
        st.Page("ui/pages/pipeline.py", title="Mettre à jour la base de données"),
    ],
    "Compétences": [
        st.Page("ui/pages/jobs.py", title="Fiches métiers"),
        st.Page("ui/pages/skills.py", title="Liste des compétences"),
    ],
    "Recherche": [
        st.Page("ui/pages/search.py", title="Recherche par métier"),
    ],
}


@st.dialog("Attention")
def leaving_page(current_page):
    st.write("Les modifications non sauvegardées seront perdues")
    col1, col2 = st.columns([1, 1])
    with col2:
        if st.button("Confirmer", width="stretch"):
            if current_page.title == "Fiches métiers":
                st.session_state.jobs_modified = False
            elif current_page.title == "Liste des compétences":
                st.session_state.skills_modified = []
            st.rerun()
    with col1:
        if st.button("Annuler", width="stretch"):
            st.switch_page(current_page)
            st.rerun()


@st.dialog("Attention")
def lauch_analyze(current_page):
    st.write("La liste des compétences a été modifiée. L'analyse des CV doit être relancée pour que les changements soient pris en compte.")
    col1, col2 = st.columns([1, 1])
    with col2:
        if st.button("Relancer l'analyse", width="stretch"):
            st.session_state.skills_saved = False
            # ✅ S'assure que pipeline_manager existe
            if "pipeline_manager" not in st.session_state:
                from core.pipManager import PipelineManager
                st.session_state.pipeline_manager = PipelineManager()
            pm = st.session_state.pipeline_manager
            pm.step = 5
            pm.running = True
            pm.done = False
            pm.error = ""
            threading.Thread(target=pm.run, args=("all",), daemon=True).start()
            # ✅ switch_page force la navigation immédiatement
            st.switch_page(pages["Gestion de la base de données"][0])
    with col1:
        if st.button("Ignorer", width="stretch"):
            st.session_state.skills_saved = False
            st.rerun()
if "error_count" not in st.session_state:
    st.session_state.error_count = 0

if "current_page" not in st.session_state:
    st.session_state.current_page = "init"
if "previous_page" not in st.session_state:
    st.session_state.previous_page = ""

if "skills_modified" not in st.session_state:
    st.session_state.skills_modified = []
if "available_skills" not in st.session_state:
    st.session_state.available_skills = []
if "selected_skills" not in st.session_state:
    st.session_state.selected_skills = pd.DataFrame({"skills": [None]}, index=[0])


try:
    future_page = ""
    if st.session_state.current_page == "init" or st.session_state.current_page == "token" or st.session_state.current_page == "token_input":
        INIT_PAGES[st.session_state.current_page]()
    else:
        st.session_state.previous_page = st.session_state.current_page
        future_page = st.navigation(pages, position="sidebar")

        if st.session_state.previous_page.title == "Liste des compétences" and len(st.session_state.skills_modified) != 0 and future_page.title != "Liste des compétences":
            leaving_page(st.session_state.previous_page)
            future_page = st.session_state.current_page
            print("attention fichier non sauvegardé")

        elif st.session_state.previous_page.title == "Liste des compétences" and st.session_state.skills_saved == True and future_page.title != "Liste des compétences":
            lauch_analyze(st.session_state.previous_page)

        elif st.session_state.previous_page.title == "Fiches métiers" and st.session_state.jobs_modified and future_page.title != "Fiches métiers":
            if st.session_state.jobs_saved == True:
                st.session_state.current_page = future_page
                st.session_state.current_page.run()
            else:
                leaving_page(st.session_state.previous_page)
                future_page = st.session_state.current_page
                print("attention fichier non sauvegardé")

        else:
            st.session_state.current_page = future_page
            st.session_state.current_page.run()

except Exception as e:
    st.session_state.error_count += 1

    if st.session_state.error_count <= 2:
        st.rerun()
    else:
        st.session_state.error_count = 0
        st.error(f"Erreur persistante : {e}")
        if st.button("Réessayer"):
            st.rerun()