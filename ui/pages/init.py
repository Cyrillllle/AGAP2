import streamlit as st
import time

def render() :
    st.title("Initialisation")

    # st.markdown("## Initialisation")

    with st.spinner("Recherche de mise à jour..."):
        time.sleep(1)
        success = True
        if success:
            st.session_state.current_page = "token"
            st.rerun()
    return True