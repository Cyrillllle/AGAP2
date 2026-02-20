# import streamlit as st
# import json
# from pathlib import Path

# SKILLS_FILE = Path("skills.json")

# print(SKILLS_FILE)

# # -------------------------
# # Chargement / sauvegarde
# # -------------------------

# def load_skills():
#     if not SKILLS_FILE.exists():
#         return {}
#     with open(SKILLS_FILE, "r", encoding="utf-8") as f:
#         return json.load(f)


# def save_skills(data):
#     with open(SKILLS_FILE, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=4, ensure_ascii=False)


# # -------------------------
# # UI
# # -------------------------

# st.set_page_config(page_title="Skills Editor", layout="wide")

# st.title("Éditeur de référentiel de compétences")

# skills_data = load_skills()

# if not skills_data:
#     st.warning("Aucun fichier skills.json trouvé. Création d'un nouveau.")
#     skills_data = {"languages": [], "frameworks": [], "methodologies": [], "tools": []}


# # -------------------------
# # Ajouter une catégorie
# # -------------------------

# st.sidebar.header("Ajouter une catégorie")

# new_category = st.sidebar.text_input("Nom de la catégorie")

# if st.sidebar.button("Créer la catégorie"):
#     if new_category and new_category not in skills_data:
#         skills_data[new_category] = []
#         save_skills(skills_data)
#         st.rerun()


# # -------------------------
# # Affichage et édition
# # -------------------------

# for category in skills_data:

#     st.subheader(f" {category}")

#     skills_list = skills_data[category]

#     # Ajouter un skill
#     col1, col2 = st.columns([3, 1])
#     new_skill = col1.text_input(f"Ajouter un skill à {category}", key=f"add_{category}")

#     col2.space("small")

#     if col2.button("Ajouter", key=f"btn_{category}"):
#         if new_skill and new_skill.lower() not in skills_list:
#             skills_data[category].append(new_skill.lower())
#             save_skills(skills_data)
#             st.rerun()

#     # Edition tableau
#     edited = st.data_editor(
#         [{"skill": s} for s in skills_list],
#         num_rows="delete",
#         key=f"editor_{category}",
#         use_container_width=True
#     )

#     # Mise à jour
#     updated_list = [row["skill"].lower() for row in edited if row["skill"].strip() != ""]

#     if updated_list != skills_list:
#         skills_data[category] = sorted(list(set(updated_list)))
#         save_skills(skills_data)
#         st.success(f"{category} mis à jour !")


# # -------------------------
# # Sauvegarde manuelle
# # -------------------------

# if st.button("Sauvegarder tout"):
#     save_skills(skills_data)
#     st.success("Fichier sauvegardé !")