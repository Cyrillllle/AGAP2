import streamlit as st
from api import client
from ui.pages import init, fetch, show, api_token
from api.client import api_request, RequestType, GetAllUsers, SearchUser 




def render() :
    st.title("Recherche")

    st.text_input("Rechercher un profil")

    return True
