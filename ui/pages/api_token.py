import streamlit as st
import time
import pathlib
import shelve
import time
import hashlib
import requests
from dataclasses import dataclass
import json
import sqlite3
from api.client import api_request, RequestType, GetAllUsers, SearchUser 
from core.storage import TOKEN_PATH



@st.dialog("Attention")
def invalid_token_dialog() :
    if st.session_state.token_state == 1 :
        st.write("Le token sauvegardé n'est plus valide")
    elif st.session_state.token_state == 2 :
        st.write("Aucun token n'a été trouvé")

    if st.button("OK"):
        st.session_state.token_state = 0
        # st.session_state.current_page = "token_input"
        st.rerun()

def token_get() :
    st.title("Initialisation")
    st.markdown("## Veuillez renseigner votre token")

    st.write("Vous trouverez vos Clef et Secret API à l'addresse suivante :\n")
    st.write("https://showcase.doyoubuzz.com/a/settings/api")
    st.write("\n")
    st.write("\n")

    if st.session_state.token_state != 0 :
        invalid_token_dialog()

    api_key    = st.text_input("Clef API")
    api_secret = st.text_input("Secret API")
    button_state = not(api_key and api_secret)

    
    
    # with st.form("test", enter_to_submit=False) :
    if st.button("Valider", disabled=not(api_key and api_secret)) :
        message = st.empty()
        message.empty()
        test_result = test_token(api_key, api_secret)
    
        if test_result :
            currentPath = pathlib.Path(__file__).parent.resolve()
            token = shelve.open(str(TOKEN_PATH))
            token["api_key"] = api_key
            token["api_secret"] = api_secret
            print("token saved")
            token.close()
            message.success("Token enregistré avec succès")
            with st.spinner("Redirection en cours...") :
                time.sleep(4)
                st.session_state.current_page = "show"
                st.rerun()
        else :
            message.error("Le token entré n'est pas valide")
    return True


def test_token(key, secret) :
    with st.spinner("Vérification du token...") :
        try : 
            status_code = api_request(secret, RequestType.GET_ALL_USERS , GetAllUsers(key, "", "admin", 1, 100)).status_code
            if status_code == 200 :
                result = True
            else : 
                result = False
        except Exception as e :
            print(e)
            result = False
    return result


def render() :
    st.title("Initialisation")
    currentPath = pathlib.Path(__file__).parent.resolve()
    token = shelve.open(str(TOKEN_PATH))
    token_keys = list(token.keys())
    token_keys.sort()
    check_result = False
    print("reading token")
    if "api_key" not in token_keys or "api_secret" not in token_keys :
        token.close()
        st.session_state.token_state = 2
        st.session_state.current_page = "token_input"
        st.rerun()
    else : 
        key = token["api_key"]
        secret = token["api_secret"]
        token.close()
        check_result = test_token(key, secret)
        if check_result :
            st.session_state.current_page = "show"
            st.rerun()
        else : 
            print("dialog")
            st.session_state.token_state = 1
            st.session_state.current_page = "token_input"
            # os.remove(str(currentPath) + "\\" + "vault")
            st.rerun()
    return check_result


