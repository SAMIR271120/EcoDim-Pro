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
/* ── Stepper vertical sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stButton"] > button {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    text-align: left !important;
    width: 100% !important;
    border: none !important;
    background-color: transparent !important;
    color: #475569 !important;
    padding: 0.42rem 0.85rem !important;
    border-radius: 6px !important;
    margin-bottom: 0.1rem !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 400 !important;
    transition: background 0.12s ease !important;
    line-height: 1.35 !important;
    gap: 6px !important;
}
/* Cibler les wrappers internes que Streamlit ajoute */
[data-testid="stSidebar"] [data-testid="stButton"] > button > div,
[data-testid="stSidebar"] [data-testid="stButton"] > button p {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    text-align: left !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    gap: 6px !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    background-color: #F1F5F9 !important;
    color: #1E293B !important;
}
/* Bouton actif (type=primary) — surbrillance ambre */
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] {
    background-color: #FDF2E2 !important;
    color: #92600A !important;
    font-weight: 600 !important;
    border-left: 3px solid #E8A33D !important;
    border-radius: 0 6px 6px 0 !important;
    padding-left: 0.7rem !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] > div,
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"] p {
    color: #92600A !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #FDEAC8 !important;
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


# ── Icônes SVG Lucide (stroke cohérent 1.75, taille 16×16) ──────────────────
_SVG = {
    # user-circle
    1: '<circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>',
    # map-pin
    2: '<path d="M12 2C8.69 2 6 4.69 6 8c0 5 6 13 6 13s6-8 6-13c0-3.31-2.69-6-6-6z"/><circle cx="12" cy="8" r="2"/>',
    # layers
    3: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    # zap
    4: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    # droplet
    5: '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
    # sun
    6: '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    # trending-up
    7: '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    # bar-chart-2
    8: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
}

def _icon_svg(step: int, color: str, size: int = 16) -> str:
    paths = _SVG.get(step, '')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" '
        f'style="display:inline-block;vertical-align:middle;flex-shrink:0;">'
        f'{paths}</svg>'
    )


def _step_valid(st, step: int) -> bool:
    """Retourne True si l'étape est considérée comme complétée (critère minimal).
    L'étape 8 (Résultats) n'est jamais auto-complétée — elle n'a pas de données propres.
    """
    ss = st.session_state
    if step == 1:
        return bool(ss.get("client_prenom") and ss.get("client_nom"))
    if step == 2:
        lat = ss.get("latitude", 0.0)
        lon = ss.get("longitude", 0.0)
        return bool(ss.get("adresse_formatee") and (lat != 0.0 or lon != 0.0))
    if step == 3:
        return bool(ss.get("surface_m2", 0) > 0 and ss.get("umur_periode"))
    if step == 4:
        appareils = ss.get("appareils_list") or []
        appareils_ok = len([a for a in appareils if a.get("nom")]) > 0
        return bool(
            ss.get("elec_annuel_kwh", 0.0) > 0
            or ss.get("conso_horaire_csv") is not None
            or appareils_ok
        )
    if step == 5:
        return bool(ss.get("nb_personnes", 0) > 0)
    if step == 6:
        pans = ss.get("pans_toiture") or []
        panneaux_par_pan = ss.get("panneaux_par_pan") or {}
        has_panels = isinstance(panneaux_par_pan, dict) and sum(panneaux_par_pan.values()) > 0
        return bool(ss.get("panneau_choisi_id") and (has_panels or ss.get("kwp_pvgis", 0.0) > 0))
    if step == 7:
        return bool(ss.get("prix_reseau", 0.0) > 0 and ss.get("duree_financement", 0) > 0)
    if step == 8:
        # Jamais auto-complétée : l'utilisateur doit atteindre cette étape manuellement
        return False
    return False


def render_stepper_sidebar(st):
    """Stepper vertical des 8 étapes avec icônes Material natives Streamlit.
    Navigation libre : cliquer sur n'importe quelle étape change current_step.
    """
    ETAPES = [
        (1, "Client & Installateur"),
        (2, "Localisation"),
        (3, "Isolation & Enveloppe"),
        (4, "Électricité"),
        (5, "ECS & Chauffage"),
        (6, "Solaire"),
        (7, "Économie"),
        (8, "Résultats"),
    ]
    current = st.session_state.get("current_step", 1)

    # ── Material icons nativement supportés par Streamlit ──────────────────
    ICONS = {
        1: ":material/person:",
        2: ":material/location_on:",
        3: ":material/layers:",
        4: ":material/bolt:",
        5: ":material/water_drop:",
        6: ":material/wb_sunny:",
        7: ":material/trending_up:",
        8: ":material/bar_chart:",
    }

    with st.sidebar:
        # Titre de section
        st.markdown(
            "<p style='font-size:.68rem;font-weight:700;letter-spacing:.09em;"
            "text-transform:uppercase;color:#94A3B8;margin:0 0 6px 2px;'>"
            "Étapes de l'étude</p>",
            unsafe_allow_html=True
        )

        for num, label in ETAPES:
            done   = _step_valid(st, num)
            active = (num == current)

            # Suffixe de statut — texte natif Streamlit
            if active:
                suffix = ""
                btn_type = "primary"
            elif done:
                suffix = " ✓"
                btn_type = "secondary"
            else:
                suffix = ""
                btn_type = "secondary"

            icon = ICONS.get(num, "")
            # Label : "icon  N. Titre  ✓"
            btn_label = f"{icon}  {num}. {label}{suffix}"

            if st.button(btn_label, key=f"step_nav_{num}",
                         type=btn_type, use_container_width=True):
                st.session_state["current_step"] = num
                st.rerun()

        st.divider()




def creer_jauge(go, valeur_pourcentage: float, titre: str, couleur: str):
    """Cree une jauge Plotly semi-circulaire pour les taux (autoconso, couverture...)."""
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
