import streamlit as st
import threading
from core.pipManager import PipelineManager


if "pipeline_manager" not in st.session_state:
    st.session_state.pipeline_manager = PipelineManager()

pm = st.session_state.pipeline_manager

STEPS = [
    "Récupération des profils",
    "Recherche des CV",
    "Téléchargement des CV",
    "Dépouillement des CV",
    "Analyse des CV"
]

@st.fragment(run_every=0.5)
def progress_fragment():
    if pm.running:
        st.progress(pm.progress, text=pm.message)
        with st.status(f"Étape {pm.step}/{len(STEPS)}", expanded=True):
            for i, step_name in enumerate(STEPS):
                if i < pm.step - 1:
                    st.write(f"~~{step_name}~~")
                elif i == pm.step - 1:
                    st.write(f"**{step_name}**")

    if pm.done and not pm.running:
        st.success("Traitement terminé ✅")

    if pm.error:
        st.error(pm.error)


st.title("Gestion de la base de données")

select_all = st.checkbox("Select all", disabled=pm.running, key="select_all_checkbox")
selection = st.selectbox(
    "Filter les profils à télécharger :",
    ["", "Industrie", "IT"],
    disabled=pm.running or select_all,
    key="filter_selectbox"
)

if not pm.running:
    selected = "all" if select_all else selection
    if st.button("Créer/mettre à jour la base de données", disabled=(selected == ""), key="start_button"):
        threading.Thread(target=pm.run, args=(selected,), daemon=True).start()
        pm.running = True
        st.rerun()
else:
    st.button("Stop", on_click=pm.stop, key="stop_button")

progress_fragment()