import streamlit as st
import threading
import time
from core.pipManager import PipelineManager
from streamlit_autorefresh import st_autorefresh



if "pipeline_manager" not in st.session_state:
    st.session_state.pipeline_manager = PipelineManager()



def render():
    pm = st.session_state.pipeline_manager

    st.title("Gestion de la base de données")

    container = st.container()

    select_all = st.checkbox(
        "Select all",
        disabled=pm.running,
        key="select_all_checkbox"
    )

    selection = container.selectbox(
        "Filter les profils à télécharger :",
        ["", "Industrie", "IT"],
        disabled=pm.running or select_all,
        key="filter_selectbox"
    )

    if not pm.running:
        selected = "all" if select_all else selection
        run_button = st.button("Créer/mettre à jour la base de données", disabled=(selected == ""), key="start_button")
        if run_button :
            threading.Thread(target=pm.run, args=(selected,), daemon=True).start()
            pm.running = True
    else:
        st.button("Stop", on_click=pm.stop, key="stop_button")

    if pm.running:
        st.progress(pm.progress, text=pm.message)
        step_status = st.status(f"Etape {pm.step}/3", expanded=True)
        if pm.step == 1 :
            step_status.write("Téléchargement des CV")
        elif pm.step == 2 :
            step_status.write("~~Téléchargement des CV~~")
            step_status.write("Dépouillement des CV")
        st_autorefresh(interval=500, key="refresh_job")

    if pm.done == True and pm.running == False :
        print(pm.done)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(pm.running)
        st.success("Traitement terminé")

    if pm.error:
        st.error(pm.error)

    # selection = st.selectbox(
    #     "Filtrer les profils",
    #     ["all", "Industrie", "IT"],
    #     disabled=pm.running
    # )

    # col1, col2 = st.columns(2)

    # with col1:
    #     if st.button(
    #         "Mettre à jour et analyser les CV",
    #         disabled=pm.running
    #     ):
    #         threading.Thread(
    #             target=pm.run,
    #             args=(selection,),
    #             daemon=True
    #         ).start()

    # with col2:
    #     if st.button(
    #         "Stop",
    #         disabled=not pm.running
    #     ):
    #         pm.stop()

    # if pm.running:
    #     st.progress(pm.progress, text=pm.message)
    #     st.info("Traitement en cours…")

    # if not pm.running and pm.progress == 1.0:
    #     st.success("Pipeline terminé")

    #     s = pm.stats
    #     st.markdown(f"""
    #     **Résumé**
    #     - Profils vus : {s.users_seen}
    #     - Profils mis à jour : {s.users_updated}
    #     - CV téléchargés : {s.cvs_downloaded}
    #     - CV parsés : {s.cvs_parsed}
    #     - CV analysés : {s.cvs_analyzed}
    #     - Erreurs : {len(s.errors)}
    #     """)
