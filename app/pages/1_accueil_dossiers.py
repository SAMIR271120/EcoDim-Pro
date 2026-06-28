"""
app/pages/1_accueil_dossiers.py — Gestion des dossiers d'études
Page d'accueil : créer un nouveau dossier ou sélectionner un dossier existant.
Un dossier sélectionné ou créé déclenche une redirection automatique vers l'étude.
"""
import sys
from pathlib import Path
root_path = str(Path(__file__).resolve().parent.parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import streamlit as st
from ecodimpro.session import init_session, get_default_etude, charger_etude, sauvegarder_etude_courante
from ecodimpro.ui import inject_css, render_sidebar

st.set_page_config(
    page_title="EcoDim Pro — Gestion des Dossiers",
    page_icon="logo/ecodimpro_favicon_64_1.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css(st)

def _charger(idx):  charger_etude(st.session_state, idx)
def _sauvegarder(): sauvegarder_etude_courante(st.session_state)

init_session(st.session_state)
render_sidebar(st)

# ─── EN-TÊTE ─────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 class='main-title'><span style='color:#E8A33D;'>•</span> EcoDim Pro</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p class='sub-title'>Simulateur professionnel de dimensionnement photovoltaïque et thermique résidentiel — méthode 3CL-DPE.</p>",
    unsafe_allow_html=True
)

# ─── DEUX COLONNES : Sélection | Création ────────────────────────────────────
st.markdown('<div class="card-neutre"><h4>Espace de Gestion des Études</h4>Créez un nouveau dossier ou sélectionnez un dossier existant pour démarrer l\'étude.</div>', unsafe_allow_html=True)

col_sel, col_creer = st.columns(2, gap="large")

# ── Sélection d'un dossier existant ──────────────────────────────────────────
with col_sel:
    st.markdown('<div class="card-neutre"><h4>Sélectionner une Étude Existante</h4></div>', unsafe_allow_html=True)

    etudes = st.session_state["etudes"]
    etudes_labels = [
        f"{i+1}.  {et['nom_etude']} — {et['client_prenom']} {et['client_nom']}"
        for i, et in enumerate(etudes)
    ]
    idx_actuel = st.session_state.get("active_etude_idx", 0)

    selected = st.selectbox(
        "Choisir le dossier",
        options=range(len(etudes_labels)),
        index=idx_actuel,
        format_func=lambda x: etudes_labels[x],
        key="etude_selector_accueil"
    )

    etude_sel = etudes[selected]
    st.markdown(f"""
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:.8rem 1rem; margin:.6rem 0; font-size:.85rem;">
        <strong>{etude_sel['nom_etude']}</strong><br>
        <span style="color:#64748B;">Client :</span> {etude_sel['client_prenom']} {etude_sel['client_nom']}<br>
        <span style="color:#64748B;">Adresse :</span> {etude_sel.get('adresse_formatee','—')}
    </div>""", unsafe_allow_html=True)

    if st.button(
        ":material/folder_open: Ouvrir ce dossier",
        use_container_width=True,
        type="primary",
        key="btn_ouvrir"
    ):
        _sauvegarder()
        st.session_state["active_etude_idx"] = selected
        _charger(selected)
        st.switch_page("pages/2_etude.py")

# ── Création d'un nouveau dossier ─────────────────────────────────────────────
with col_creer:
    st.markdown('<div class="card-neutre"><h4>Créer un Nouveau Dossier</h4></div>', unsafe_allow_html=True)

    with st.form("form_new_etude_accueil", clear_on_submit=True):
        nouveau_nom    = st.text_input("Nom du projet", placeholder="ex: Villa Soleil — Bordeaux")
        nouveau_prenom = st.text_input("Prénom du propriétaire", placeholder="ex: Albert")
        nouveau_nom_cl = st.text_input("Nom du propriétaire", placeholder="ex: Mercier")

        btn_creer = st.form_submit_button(
            ":material/add: Créer et ouvrir le dossier",
            use_container_width=True
        )

        if btn_creer:
            nom_saisi = nouveau_nom.strip()
            if not nom_saisi:
                st.error("Veuillez saisir un nom de projet.")
            else:
                _sauvegarder()
                prenom_c = nouveau_prenom.strip() or "Nouveau"
                nom_c    = nouveau_nom_cl.strip()  or "Client"
                nouvelle_etude = get_default_etude(
                    nom_etude=nom_saisi, client_prenom=prenom_c, client_nom=nom_c
                )
                st.session_state["etudes"].append(nouvelle_etude)
                new_idx = len(st.session_state["etudes"]) - 1
                st.session_state["active_etude_idx"] = new_idx
                _charger(new_idx)
                st.switch_page("pages/2_etude.py")

# ─── TABLEAU DE TOUS LES DOSSIERS ────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="card-neutre"><h4>Tous les Dossiers</h4></div>', unsafe_allow_html=True)

for i, et in enumerate(st.session_state["etudes"]):
    is_active = (i == st.session_state.get("active_etude_idx", 0))
    badge = "  🟢 *actif*" if is_active else ""
    with st.expander(f"**{et['nom_etude']}**{badge} — {et['client_prenom']} {et['client_nom']}"):
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.write(f"**Email :** {et.get('client_email','—')}")
        c2.write(f"**Adresse :** {et.get('adresse_formatee','—')}")
        c3.write(f"**Isolation :** {et.get('niveau_isolation','—')}")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if not is_active:
                if st.button(":material/folder_open: Activer et ouvrir", key=f"activer_{i}", use_container_width=True):
                    _sauvegarder()
                    st.session_state["active_etude_idx"] = i
                    _charger(i)
                    st.switch_page("pages/2_etude.py")
            else:
                st.info("🟢 Dossier actuellement actif")

        with col_btn2:
            if len(st.session_state["etudes"]) > 1:
                # Bouton de suppression rouge discret
                if st.button(":material/delete: Supprimer ce dossier", key=f"supprimer_{i}", use_container_width=True, type="secondary"):
                    active_idx = st.session_state.get("active_etude_idx", 0)
                    st.session_state["etudes"].pop(i)
                    
                    # Réajustement de l'index actif
                    if active_idx == i:
                        new_active = max(0, i - 1)
                        st.session_state["active_etude_idx"] = new_active
                        _charger(new_active)
                    elif active_idx > i:
                        st.session_state["active_etude_idx"] = active_idx - 1
                        
                    st.success("Le dossier a été supprimé.")
                    st.rerun()
            else:
                st.caption("Dossier unique — impossible de le supprimer.")

_sauvegarder()
