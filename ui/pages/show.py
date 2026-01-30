import streamlit as st
from api import client
from ui.pages import init, fetch, show, api_token

def render() :
    st.title("Show")
    return True

