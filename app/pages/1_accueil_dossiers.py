"""
app/pages/1_accueil_dossiers.py — Gestion des dossiers d'études
PAGE 1 — Mes Dossiers  : liste des études existantes + bouton + Nouveau dossier
PAGE 2 — Nouveau Dossier : formulaire de création (vue déclenchée par le bouton)
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
    page_title="EcoDim Pro — Mes Dossiers",
    page_icon="logo/ecodimpro_favicon_64_1.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css(st)

def _charger(idx):  charger_etude(st.session_state, idx)
def _sauvegarder(): sauvegarder_etude_courante(st.session_state)

init_session(st.session_state)

if "view_accueil" not in st.session_state:
    st.session_state["view_accueil"] = "list"

render_sidebar(st)

# ══════════════════════════════════════════════════════════════════════════════
# VUE 1 — MES DOSSIERS
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["view_accueil"] == "list":

    col_titre, col_btn_new = st.columns([3, 1])
    with col_titre:
        st.markdown(
            "<h1 class='main-title'><span style='color:#E8A33D;'>•</span> Mes Dossiers</h1>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p class='sub-title'>Sélectionnez un dossier pour reprendre l'étude, ou créez-en un nouveau.</p>",
            unsafe_allow_html=True
        )
    with col_btn_new:
        st.write("")
        st.write("")
        if st.button(":material/add: Nouveau dossier", type="primary",
                     use_container_width=True, key="btn_nouveau_dossier"):
            st.session_state["view_accueil"] = "create"
            st.rerun()

    st.markdown("---")

    etudes = st.session_state.get("etudes", [])

    if not etudes:
        st.markdown("""
        <div style="
            text-align:center; padding:3rem 2rem; margin:2rem auto; max-width:480px;
            background:#FFFFFF; border:1px dashed #CBD5E1; border-radius:10px;
            box-shadow:0 1px 3px rgba(0,0,0,.04);
        ">
            <div style="font-size:2.5rem; margin-bottom:0.8rem;">📂</div>
            <h3 style="font-family:'Space Grotesk',sans-serif; color:#1E293B; margin:0 0 .5rem;">
                Aucun dossier pour l'instant
            </h3>
            <p style="color:#64748B; font-size:.9rem; margin:0;">
                Cliquez sur <strong>+ Nouveau dossier</strong> pour créer votre première étude.
            </p>
        </div>
        """, unsafe_allow_html=True)

    else:
        idx_actuel = st.session_state.get("active_etude_idx")

        for i, et in enumerate(etudes):
            is_active = (i == idx_actuel)
            border_color = "#E8A33D" if is_active else "#E2E8F0"
            badge_html = (
                "<span style='background:#FDF2E2; color:#B07A2A; font-size:.72rem; "
                "font-weight:600; padding:.15rem .5rem; border-radius:99px; "
                "margin-left:.5rem;'>● Actif</span>"
                if is_active else ""
            )

            nom     = et.get("nom_etude", "Sans nom")
            prenom  = et.get("client_prenom", "")
            nom_cl  = et.get("client_nom", "")
            adresse = et.get("adresse_formatee", "") or "—"
            email   = et.get("client_email", "") or "—"
            client_str = f"{prenom} {nom_cl}".strip() or "—"

            col_card, col_actions = st.columns([5, 1])

            with col_card:
                st.markdown(f"""
                <div style="
                    background:#FFFFFF;
                    border:1px solid {border_color};
                    border-left:4px solid {border_color};
                    border-radius:8px;
                    padding:1rem 1.4rem;
                    margin-bottom:.5rem;
                    box-shadow:0 1px 4px rgba(0,0,0,.06);
                ">
                    <div style="display:flex; align-items:center; gap:.4rem; margin-bottom:.3rem;">
                        <span style="font-family:'Space Grotesk',sans-serif; font-weight:700;
                                     font-size:1rem; color:#1E293B;">{nom}</span>
                        {badge_html}
                    </div>
                    <div style="font-size:.83rem; color:#475569; line-height:1.6;">
                        <span style="margin-right:1.5rem;">👤 {client_str}</span>
                        <span style="margin-right:1.5rem;">📍 {adresse}</span>
                        <span>✉️ {email}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_actions:
                st.write("")
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    ouvrir_label = ":material/edit: Continuer" if is_active else ":material/folder_open: Ouvrir"
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(ouvrir_label, key=f"ouvrir_{i}",
                                 use_container_width=True, type=btn_type):
                        _sauvegarder()
                        st.session_state["active_etude_idx"] = i
                        st.session_state["current_step"] = 1
                        _charger(i)
                        st.switch_page("pages/2_etude.py")

                with btn_col2:
                    if st.button(":material/delete:", key=f"supprimer_{i}",
                                 use_container_width=True, type="secondary"):
                        active_idx = st.session_state.get("active_etude_idx")
                        st.session_state["etudes"].pop(i)
                        if active_idx == i:
                            if st.session_state["etudes"]:
                                new_active = max(0, i - 1)
                                st.session_state["active_etude_idx"] = new_active
                                _charger(new_active)
                            else:
                                st.session_state["active_etude_idx"] = None
                        elif active_idx is not None and active_idx > i:
                            st.session_state["active_etude_idx"] = active_idx - 1
                        st.rerun()

    _sauvegarder()


# ══════════════════════════════════════════════════════════════════════════════
# VUE 2 — NOUVEAU DOSSIER
# ══════════════════════════════════════════════════════════════════════════════
else:
    col_back, col_titre_new = st.columns([1, 5])
    with col_back:
        st.write("")
        st.write("")
        if st.button(":material/arrow_back: Retour", key="btn_retour_list",
                     use_container_width=True):
            st.session_state["view_accueil"] = "list"
            st.rerun()
    with col_titre_new:
        st.markdown(
            "<h1 class='main-title'><span style='color:#E8A33D;'>+</span> Nouveau dossier</h1>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p class='sub-title'>Renseignez les informations de base pour créer un dossier d'étude vierge.</p>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    _, col_form, _ = st.columns([1, 3, 1])
    with col_form:
        st.markdown('<div class="card-neutre"><h4>Informations du dossier</h4></div>', unsafe_allow_html=True)

        with st.form("form_new_etude", clear_on_submit=True):
            nouveau_nom    = st.text_input("Nom du projet *",
                                           placeholder="ex: Villa Soleil — Bordeaux")
            nouveau_prenom = st.text_input("Prénom du propriétaire",
                                           placeholder="ex: Albert")
            nouveau_nom_cl = st.text_input("Nom du propriétaire",
                                           placeholder="ex: Mercier")
            st.caption("* Champ obligatoire")

            col_submit, col_cancel = st.columns(2)
            with col_submit:
                btn_creer = st.form_submit_button(
                    ":material/add: Créer et ouvrir",
                    use_container_width=True, type="primary"
                )
            with col_cancel:
                btn_annuler = st.form_submit_button(
                    ":material/close: Annuler",
                    use_container_width=True
                )

            if btn_creer:
                nom_saisi = nouveau_nom.strip()
                if not nom_saisi:
                    st.error("Veuillez saisir un nom de projet avant de continuer.")
                else:
                    _sauvegarder()
                    nouvelle_etude = get_default_etude(
                        nom_etude=nom_saisi,
                        client_prenom=nouveau_prenom.strip(),
                        client_nom=nouveau_nom_cl.strip()
                    )
                    st.session_state["etudes"].append(nouvelle_etude)
                    new_idx = len(st.session_state["etudes"]) - 1
                    st.session_state["active_etude_idx"] = new_idx
                    st.session_state["current_step"] = 1
                    st.session_state["view_accueil"] = "list"
                    _charger(new_idx)
                    st.switch_page("pages/2_etude.py")

            if btn_annuler:
                st.session_state["view_accueil"] = "list"
                st.rerun()
