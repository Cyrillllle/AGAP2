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


# ── Dialogs ───────────────────────────────────────────────────────────
@st.dialog("CV du candidat", width="large")
def show_cv(cv_id):
    pdf_data = load_pdf(cv_id)
    st.pdf(pdf_data)


@st.dialog("Compétences du candidat", width="large")
def show_skills_popup(candidate_name, cv_id):
    st.markdown(f"### {candidate_name}")
    skills = get_user_skills(cv_id)
    if not skills:
        st.info("Aucune compétence enregistrée.")
        return

    st.markdown("""
    <style>
    .popup-skill-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.4rem 0;
        border-bottom: 1px solid #2a3147;
        font-family: 'DM Mono', monospace;
        font-size: 0.82rem;
    }
    .popup-skill-name { color: #f1f5f9; }
    .popup-skill-bar-wrap {
        flex: 1;
        margin: 0 1rem;
        height: 4px;
        background: #1b2135;
        border-radius: 2px;
    }
    .popup-skill-bar {
        height: 4px;
        background: #ff6b6b;
        border-radius: 2px;
    }
    .popup-skill-months { color: #7a8099; font-size: 0.72rem; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

    max_months = max(m for _, m in skills) if skills else 1

    rows_html = ""
    for skill_name, months in skills:
        pct = int((months / max_months) * 100)
        exp_str = format_exp(months)
        rows_html += f"""
        <div class="popup-skill-row">
            <span class="popup-skill-name">{skill_name}</span>
            <div class="popup-skill-bar-wrap">
                <div class="popup-skill-bar" style="width:{pct}%"></div>
            </div>
            <span class="popup-skill-months">{exp_str}</span>
        </div>"""

    st.markdown(rows_html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Voir CV"):
        show_cv(cv_id)


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


def render_candidate_card(r, card_key, highlighted_skills=None, required_groups=None):
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

    top_skills = sorted_skills[:6]
    rest_skills = sorted_skills[6:]

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

    rest_label = f'<span class="skill-tag" style="color:#7a8099;cursor:pointer">+{len(rest_skills)} autres</span>' if rest_skills else ""

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
        <div class="skills-grid">{top_html}{rest_label}</div>
    </div>
    """

    # ✅ Colonnes : carte | bouton skills | bouton CV
    col_card, col_skills, col_cv = st.columns([3, 1, 1])
    with col_card:
        st.markdown(card_html, unsafe_allow_html=True)
    with col_skills:
        st.space("xsmall")
        st.markdown("<div style='padding-top:1.1rem'></div>", unsafe_allow_html=True)
        if st.button("Voir compétences", key=f"skills_{card_key}"):
            show_skills_popup(r["name"], r["cv_id"])
    with col_cv:
        st.space("xsmall")
        st.markdown("<div style='padding-top:1.1rem'></div>", unsafe_allow_html=True)
        if st.button("voir CV", key=f"cv_{card_key}"):
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
        # ✅ clé unique avec préfixe "nom" pour éviter collision avec tab poste
        r["skills"] = dict(get_user_skills(r["cv_id"]))
        render_candidate_card(r, f"nom_{r['cv_id']}")


# ── Page ─────────────────────────────────────────────────────────────
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

results = []
highlighted = []
required_groups = []

selected_job = st.selectbox("Poste", ["(aucun)"] + job_names)

if selected_job != "(aucun)":
    required_groups, optional_flat = get_job_requirements(job_data, selected_job)
    highlighted = [s for group in required_groups for s in group] + optional_flat
    logic_str = " ET ".join([f"({' OU '.join(g)})" for g in required_groups])
    st.caption(f"Filtre actif : {logic_str}")
    results = search_multi_groups(required_groups, optional_flat, 1)

if results and required_groups:
    for r in results:
        skills_lower = {k.lower(): v for k, v in r.get("skills", {}).items()}
        groups_lower = [[s.lower() for s in g] for g in required_groups]
        r["_min_exp"] = compute_min_exp(skills_lower, groups_lower) or 0

    max_min_exp = max(r["_min_exp"] for r in results)
    if max_min_exp > 0:
        max_years = max(1, max_min_exp // 12)
        filter = st.slider(
            "Expérience recherchée (années)",
            min_value=0, max_value=int(max_years), value=(0,int(max_years)), step=1
        )
        results = [r for r in results if r["_min_exp"] >= filter[0] * 12 and r["_min_exp"] <= filter[1] * 12]

if results:
    n = len(results)
    st.markdown(
        f'<div class="results-count"><span>{n}</span> profil{"s" if n > 1 else ""} trouvé{"s" if n > 1 else ""}</div>',
        unsafe_allow_html=True
    )
    for i, r in enumerate(results):
        # ✅ clé unique avec cv_id pour éviter les doublons
        render_candidate_card(r, f"poste_{r['cv_id']}", highlighted_skills=highlighted, required_groups=required_groups)
elif selected_job != "(aucun)":
    st.markdown('<div class="results-count"><span>0</span> résultat</div>', unsafe_allow_html=True)