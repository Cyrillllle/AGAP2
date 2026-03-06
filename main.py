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

# PAGES = {
#     "show"       : show.render, 
#     "fetch"      : fetch.render, 
#     "Analyse"    : anaParse.render,
#     "Pipeline"   : pipeline.render,
#     "search"     : search.render,
#     "jobs"       : jobs.render
# }

# état initial
if "current_page" not in st.session_state:
    st.session_state.current_page = "init"
#     # affichage de la page courante

if "available_skills" not in st.session_state :
    st.session_state.available_skills = []
if "selected_skills" not in st.session_state :
    st.session_state.selected_skills = pd.DataFrame({"skills": [None]}, index=[0])



# else : 
#     st.sidebar.title("Navigation")
#     selection = st.sidebar.radio("Aller à", list(PAGES.keys()))
#     PAGES[selection]()

print("aaa")

pages = {
    "Profils": [
        st.Page("ui/pages/pipeline.py", title="Gérer la base de données"),
        # st.Page("manage_account.py", title="Manage your account"),
    ],
    "Jobs": [
        st.Page("ui/pages/jobs.py", title="Learn about us"),
        # st.Page("trial.py", title="Try it out"),
    ],
    "Search": [
        st.Page("ui/pages/search.py", title="Search"),
        # st.Page("trial.py", title="Try it out"),
    ],
}


if st.session_state.current_page == "init" or st.session_state.current_page == "token" or st.session_state.current_page == "token_input" :
    INIT_PAGES[st.session_state.current_page]()
else :
    st.session_state.current_page = st.navigation(pages, position="sidebar")
    st.session_state.current_page.run()

