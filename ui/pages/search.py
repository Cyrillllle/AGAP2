import streamlit as st
from api import client
from ui.pages import init, fetch, show, apiToken
from api.client import api_request, RequestType, GetAllUsers, SearchUser 
from core.database import *




def render() :
    st.title("Recherche")

    st.text_input("Rechercher un profil")
    result = search("python", 0)
    for user in result : 
        print(result[user])

    return True
