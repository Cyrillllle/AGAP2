import streamlit as st
from api import client
from ui.pages import init, fetch, show, apiToken

def render() :
    st.title("Show")
    return True

