"""
ecodimpro/ui.py
Utilitaires d'interface partagés entre toutes les pages Streamlit.
CSS premium, sidebar, jauge Plotly.
"""
import sys
from pathlib import Path

# Garantir que le root est dans le path même si importé depuis pages/
root_path = str(Path(__file__).resolve().parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)


CSS_PREMIUM = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }
h1, h2, h3, h4 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -0.01em; color: #1E293B; }

.main-title { color:#1E293B; font-family:'Space Grotesk',sans-serif !important; font-size:2.2rem; font-weight:700; margin-bottom:2px; }
.sub-title  { color:#64748B; font-family:'Inter',sans-serif; font-size:1rem; margin-bottom:20px; }

[data-testid="stMetricValue"] { font-family:'JetBrains Mono',monospace !important; font-weight:600; color:#1E293B; }

.card-pv {
    border-left:4px solid #E8A33D; background:#FFF; padding:1.2rem 1.5rem;
    border-radius:6px; border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0;
    border-bottom:1px solid #E2E8F0; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,.05);
}
.card-pv h4 {
    font-family:'Space Grotesk',sans-serif; font-size:.78rem; font-weight:700;
    letter-spacing:.08em; text-transform:uppercase; color:#B07A2A;
    margin:0 0 .4rem 0; padding-bottom:.4rem; border-bottom:1px solid #FDE8C2;
}
.card-thermique {
    border-left:4px solid #3DBFAE; background:#FFF; padding:1.2rem 1.5rem;
    border-radius:6px; border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0;
    border-bottom:1px solid #E2E8F0; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,.05);
}
.card-thermique h4 {
    font-family:'Space Grotesk',sans-serif; font-size:.78rem; font-weight:700;
    letter-spacing:.08em; text-transform:uppercase; color:#268C7E;
    margin:0 0 .4rem 0; padding-bottom:.4rem; border-bottom:1px solid #C8EDE9;
}
.card-neutre {
    border-left:4px solid #64748B; background:#FFF; padding:1.2rem 1.5rem;
    border-radius:6px; border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0;
    border-bottom:1px solid #E2E8F0; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,.05);
}
.card-neutre h4 {
    font-family:'Space Grotesk',sans-serif; font-size:.78rem; font-weight:700;
    letter-spacing:.08em; text-transform:uppercase; color:#475569;
    margin:0 0 .4rem 0; padding-bottom:.4rem; border-bottom:1px solid #E2E8F0;
}
.stTabs [data-baseweb="tab-list"] { gap:2px; }
.stTabs [data-baseweb="tab"] {
    font-family:'Space Grotesk',sans-serif; font-size:.85rem;
    font-weight:500; letter-spacing:.01em; padding:.5rem 1.1rem;
}
.stTabs [aria-selected="true"] {
    color:#E8A33D !important; border-bottom-color:#E8A33D !important; font-weight:600 !important;
}
/* Masquer la navigation native par défaut de Streamlit pour éviter le doublon */
[data-testid="stSidebarNav"] {
    display: none !important;
}
</style>
"""


def inject_css(st):
    """Injecte le CSS premium dans la page courante."""
    st.markdown(CSS_PREMIUM, unsafe_allow_html=True)


def render_sidebar(st):
    """Affiche la sidebar EcoDim Pro avec le dossier actif."""
    with st.sidebar:
        logo_container = st.container()
        if st.session_state.get("logo_bytes") is not None:
            logo_container.image(st.session_state["logo_bytes"], width=150)
        else:
            # Nouveau logo transparent de l'application EcoDim Pro (v2 pour bypass de cache)
            logo_container.image("logo/ecodimpro_logo_transparent_v2.svg", width=130)

        st.divider()
        st.markdown(":material/folder_open: **Dossier Actif**")
        st.write(f"**Client :** {st.session_state.get('client_prenom','')} {st.session_state.get('client_nom','')}")
        societe = st.session_state.get("client_societe", "")
        if societe:
            st.write(f"**Société :** {societe}")
        st.write(f"**Adresse :** {st.session_state.get('adresse_formatee','—')}")
        st.write(f"**Diagnostiqueur :** {st.session_state.get('installateur_nom','—')}")
        st.divider()
        st.caption("Navigation — EcoDim Pro")
        st.page_link("pages/1_accueil_dossiers.py", label="Accueil & Dossiers", icon=":material/home:")
        st.page_link("pages/2_etude.py",            label="Étude",              icon=":material/solar_power:")


def creer_jauge(go, valeur_pourcentage: float, titre: str, couleur: str):
    """Crée une jauge Plotly semi-circulaire pour les taux (autoconso, couverture…)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valeur_pourcentage,
        number={'suffix': "%", 'font': {'family': 'JetBrains Mono', 'size': 36, 'color': '#1E293B'}},
        title={'text': titre, 'font': {'family': 'Space Grotesk', 'size': 16, 'color': '#1E293B'}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#E2E8F0'},
            'bar': {'color': couleur},
            'bgcolor': '#F1F5F9',
            'borderwidth': 0,
            'steps': [{'range': [0, 100], 'color': '#F1F5F9'}],
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#1E293B'},
        height=250,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig
