import streamlit as st
from api import client
from ui.pages import init, fetch, show, apiToken
from api.client import api_request, RequestType, GetAllUsers, SearchUser 
from core.database import *




def render() :
    st.title("Recherche")

    st.text_input("Rechercher un profil")

    all_skills = read_skills()
    required = []
    for skill_id in all_skills :
        required.append(all_skills[skill_id])

    req_options = st.multiselect("Compétences obligatoires", required)

    st.write("You selected:", req_options)
    # required = ["python"]
    optional = ["python"]

    results = search_multi(req_options, optional, 1)
    print(results)
    st.write(results)

    return True
