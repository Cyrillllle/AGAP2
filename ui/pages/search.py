import streamlit as st
import json
from pathlib import Path
from core.database import *
from core.storage import *


# ── CSS ──────────────────────────────────────────────────────────────
def load_css():
    css_path = Path(__file__).parent.parent.parent / "search_styles.css"
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# ── Dialog ───────────────────────────────────────────────────────────
@st.dialog("CV du candidat", width="large")
def show_cv(cv_id):
    pdf_data = load_pdf(cv_id)
    st.pdf(pdf_data)


# ── Helpers ──────────────────────────────────────────────────────────
def load_job_skills(filepath=JOB_PATH):
    with open(filepath, "r") as f:
        return json.load(f)


def get_job_requirements(job_data, job_name):
    job = job_data[job_name]
    required_groups = [group for group in job["required"] if group]
    optional_groups = [skill for group in job["optional"] for skill in group if group]
    return required_groups, optional_groups


def format_exp(total_months):
    if total_months is None:
        return "?"
    total_months = int(total_months)
    if total_months >= 12:
        years = total_months // 12
        months = total_months % 12
        s = "s" if years > 1 else ""
        return f"{years} an{s}{f' {months}m' if months else ''}"
    return f"{total_months} mois"


def compute_min_exp(skills_dict, required_groups):
    if not required_groups or not skills_dict:
        return None
    group_maxes = []
    for group in required_groups:
        months_in_group = [skills_dict[s] for s in group if s in skills_dict]
        if months_in_group:
            group_maxes.append(max(months_in_group))
        else:
            return 0
    return min(group_maxes) if group_maxes else None


def render_candidate_card(r, index, highlighted_skills=None, required_groups=None):
    highlighted_skills = set(s.lower() for s in (highlighted_skills or []))
    all_skills = r.get("skills", {})

    min_exp = compute_min_exp(
        {k.lower(): v for k, v in all_skills.items()},
        [[s.lower() for s in g] for g in (required_groups or [])]
    )

    sorted_skills = sorted(
        all_skills.items(),
        key=lambda x: (x[0].lower() not in highlighted_skills, -x[1])
    )

    top_skills = sorted_skills[:8]
    rest_skills = sorted_skills[8:]

    def skill_html(skill_name, months):
        is_hl = skill_name.lower() in highlighted_skills
        cls = "skill-tag highlighted" if is_hl else "skill-tag"
        return (
            f'<span class="{cls}">'
            f'{skill_name}'
            f'<span class="skill-months">{months}m</span>'
            f'</span>'
        )

    top_html = "".join(skill_html(n, m) for n, m in top_skills)

    details_html = ""
    if rest_skills:
        rest_html = "".join(skill_html(n, m) for n, m in rest_skills)
        details_html = f"""
        <details class="card-details">
            <summary>+{len(rest_skills)} compétences</summary>
            <div class="all-skills-list">{rest_html}</div>
        </details>"""

    min_badge = ""
    if min_exp is not None:
        min_badge = f'<span class="badge badge-min">min {format_exp(min_exp)}</span>'

    card_html = f"""
    <div class="candidate-card">
        <div class="candidate-header">
            <div class="candidate-name">{r['name']}</div>
            <div class="candidate-badges">
                {min_badge}
                <span class="badge badge-exp">{format_exp(r.get('total_exp_months'))} exp.</span>
            </div>
        </div>
        <div class="skills-grid">{top_html}</div>
        {details_html}
    </div>
    """

    col_card, col_btn = st.columns([11, 1])
    with col_card:
        st.markdown(card_html, unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='padding-top:1.1rem'></div>", unsafe_allow_html=True)
        if st.button("CV", key=f"cv_{r['cv_id']}_{index}"):
            show_cv(r["cv_id"])


# ── Fragment live search par nom ──────────────────────────────────────
@st.fragment
def name_results_fragment():
    q = st.session_state.get("name_search_input", "")
    if not q.strip():
        st.markdown(
            '<div class="results-count">Tapez un nom pour rechercher</div>',
            unsafe_allow_html=True
        )
        return

    results = search_by_name(q)

    if not results:
        st.markdown(
            '<div class="results-count"><span>0</span> résultat</div>',
            unsafe_allow_html=True
        )
        return

    n = len(results)
    st.markdown(
        f'<div class="results-count"><span>{n}</span> profil{"s" if n > 1 else ""} trouvé{"s" if n > 1 else ""}</div>',
        unsafe_allow_html=True
    )
    for i, r in enumerate(results):
        r["skills"] = dict(get_user_skills(r["cv_id"]))
        render_candidate_card(r, f"name_{i}")


st.title("Recherche")

try:
    all_skills_dict = read_skills_by_id()
    all_skill_names = list(all_skills_dict.values())
except Exception:
    all_skills_dict = {}
    all_skill_names = []

try:
    job_data = load_job_skills(JOB_PATH)
    job_names = list(job_data.keys())
except Exception:
    job_data = {}
    job_names = []

if not all_skill_names and not job_names:
    st.warning("La base de données est vide. Lancez d'abord une mise à jour depuis la page 'Base de données'.")

tab_poste, tab_nom = st.tabs(["Par poste / compétences", "Par nom"])

# ── Tab 1 : recherche par poste ───────────────────────────────────────
with tab_poste:
    results = []
    highlighted = []
    required_groups = []

    col1, col2 = st.columns([2, 3])
    with col1:
        selected_job = st.selectbox("Poste", ["(aucun)"] + job_names)

    if selected_job != "(aucun)":
        required_groups, optional_flat = get_job_requirements(job_data, selected_job)
        highlighted = [s for group in required_groups for s in group] + optional_flat
        logic_str = " ET ".join([f"({' OU '.join(g)})" for g in required_groups])
        st.caption(f"Filtre actif : {logic_str}")
        results = search_multi_groups(required_groups, optional_flat, 1)
    else:
        with col2:
            req_options = st.multiselect("Compétences obligatoires", all_skill_names)
        opt_options = st.multiselect("Compétences optionnelles", all_skill_names)
        highlighted = req_options + opt_options
        required_groups = [[s] for s in req_options]
        if req_options or opt_options:
            results = search_multi(req_options, opt_options, 1)

    if results and required_groups:
        for r in results:
            skills_lower = {k.lower(): v for k, v in r.get("skills", {}).items()}
            groups_lower = [[s.lower() for s in g] for g in required_groups]
            r["_min_exp"] = compute_min_exp(skills_lower, groups_lower) or 0

        max_min_exp = max(r["_min_exp"] for r in results)
        if max_min_exp > 0:
            max_years = max(1, max_min_exp // 12)
            min_filter = st.slider(
                "Expérience minimale requise (années)",
                min_value=0, max_value=int(max_years), value=0, step=1
            )
            results = [r for r in results if r["_min_exp"] >= min_filter * 12]

    if results:
        n = len(results)
        st.markdown(
            f'<div class="results-count"><span>{n}</span> profil{"s" if n > 1 else ""} trouvé{"s" if n > 1 else ""}</div>',
            unsafe_allow_html=True
        )
        for i, r in enumerate(results):
            render_candidate_card(r, i, highlighted_skills=highlighted, required_groups=required_groups)
    elif selected_job != "(aucun)":
        st.markdown('<div class="results-count"><span>0</span> résultat</div>', unsafe_allow_html=True)

with tab_nom:
    st.text_input(
        "Nom du candidat",
        placeholder="ex: Dupont",
        key="name_search_input"
    )
    name_results_fragment()