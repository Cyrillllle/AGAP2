import streamlit as st
from api import client
import pandas as pd
from streamlit_dynamic_filters import DynamicFilters
from ui.pages import init, fetch, show, apiToken
from api.client import api_request, RequestType, GetAllUsers, SearchUser 
from core.database import *


@st.dialog("CV du candidat", width="large")
def show_cv(cv_id):
    pdf_data = load_pdf(cv_id)
    st.pdf(pdf_data)


# def render() :
st.title("Recherche")

# data = {
# 'Region': ['North America', 'North America', 'North America', 'Europe', 'Europe', 'Asia', 'Asia'],
# 'Country': ['USA', 'USA', 'Canada', 'Germany', 'France', 'Japan', 'China'],
# 'City': ['New York', 'Los Angeles', 'Toronto', 'Berlin', 'Paris', 'Tokyo', 'Beijing']
# }

# df = pd.DataFrame(data)
# dynamic_filters = DynamicFilters(df, filters=['Region', 'Country', 'City'])

# with st.sidebar:
#     dynamic_filters.display_filters()

# dynamic_filters.display_df()

st.text_input("Rechercher un profil")

all_skills = read_skills_by_id()
required = []
optional = []
for skill_id in all_skills :
    required.append(all_skills[skill_id])
    optional.append(all_skills[skill_id])

req_options = st.multiselect("Compétences obligatoires", required)

st.write("You selected:", req_options)
# required = ["python"]
req_options2 = st.multiselect("Compétences optionnelles", optional)



results = search_multi(req_options, req_options2, 1)

st.write(results)

for r in results:
    with st.expander(f"{r['name']} — {r['total_months']} mois d'expérience"):
        
        skills = get_user_skills(r["cv_id"])
        
        st.write("### Compétences :")
        for skill, months in skills:
            st.write(f"- {skill} : {months} mois")

        if st.button("Voir CV", key=f"cv_{r['cv_id']}"):
            show_cv(r['cv_id'])
    