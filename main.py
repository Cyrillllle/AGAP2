import streamlit as st
from api import client
from ui.pages import init, fetch, show, search, api_token, anaParse
from pathlib import Path


st.set_page_config(layout="wide")
st.html("<style>[data-testid='stHeaderActionElements'] {display: none;}</style>")

INIT_PAGES = {
    "init": init.render,
    "token": api_token.render,
    "token_input": api_token.token_get, 
    # "detail": detail.render,
}

PAGES = {
    "show"       : show.render, 
    "fetch"      : fetch.render, 
    "Analyse"    : anaParse.render,
    "search"     : search.render, 
}

# état initial
if "current_page" not in st.session_state:
    st.session_state.current_page = "init"
    # affichage de la page courante


if st.session_state.current_page == "init" or st.session_state.current_page == "token" or st.session_state.current_page == "token_input" :
    INIT_PAGES[st.session_state.current_page]()
else : 
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Aller à", list(PAGES.keys()))
    PAGES[selection]()


