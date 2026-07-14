"""
app/pages/2_etude.py — Étude Complète (8 étapes — Stepper vertical)
Client · Localisation · Isolation · Électricité · ECS & Chauffage · Solaire · Économie · Résultats
Méthode 3CL-DPE, arrêté 31 mars 2021.
"""
import os, sys, tempfile, re
import numpy as np
from pathlib import Path

root_path = str(Path(__file__).resolve().parent.parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

from ecodimpro.session import init_session, charger_etude, sauvegarder_etude_courante
from ecodimpro.ui import inject_css, render_sidebar, render_stepper_sidebar, creer_jauge
from ecodimpro.besoins import calc_besoin_elec, calc_besoin_ecs, calc_besoin_chauffage
from ecodimpro.pv import (production_pv_mensuelle, recuperer_irradiation_pvgis,
                           detecter_zone_climatique, DAYS_IN_MONTH,
                           calculer_nb_panneaux_max, puissance_totale_kwc)
from ecodimpro.thermique import dimensionner_ballon, couverture_ecs
from ecodimpro.batterie import gain_autoconsommation_avec_batterie
from ecodimpro.bilan import calc_autoconsommation
from ecodimpro.economie import calc_capex_pv, calc_capex_thermique, economies_annuelles, payback_simple, van
from ecodimpro.rapport import generer_rapport_pdf
from ecodimpro.geolocalisation import geocoder_adresse
from ecodimpro.equipements import charger_catalogue, filtrer_panneaux_par_surface
from ecodimpro.cablage import estimer_section_cable, estimer_metrage_cablage
from ecodimpro.constantes_dpe import (
    DH14_PAR_ZONE, DJU_BASE18_PAR_ZONE,
    PERIODES_CONSTRUCTION, PERIODE_TO_ISOLATION, U_PAR_PERIODE, LABELS_ISOLATION,
    SCENARIOS_ECS, ZONES_CLIMATIQUES,
    UMUR_PAR_PERIODE, PERIODES_UMUR, UPH_TOITURE, TYPES_TOITURE,
    UPB_PLANCHER_BAS_DEFAUT,
    ECS_LITRES_CONVENTIONNEL, ECS_TEMP_CHAUDE_CONVENTIONNEL, ECS_TEMP_FROIDE_REFERENCE,
)

st.set_page_config(
    page_title="EcoDim Pro — Étude",
    page_icon="logo/ecodimpro_favicon_64_1.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css(st)

def _charger(idx):  charger_etude(st.session_state, idx)
def _sauvegarder(): sauvegarder_etude_courante(st.session_state)

init_session(st.session_state)

# ─── Garde : redirection si pas de dossier actif ──────────────────────────────
if not st.session_state.get("etudes"):
    st.warning(":material/warning: Aucun dossier actif. Veuillez créer ou sélectionner un dossier.")
    st.page_link("pages/1_accueil_dossiers.py", label="← Aller à la gestion des dossiers",
                  icon=":material/folder_open:")
    st.stop()

active_idx = st.session_state.get("active_etude_idx")
if active_idx is None or active_idx >= len(st.session_state["etudes"]):
    st.warning(":material/warning: Aucun dossier actif. Veuillez sélectionner un dossier.")
    st.page_link("pages/1_accueil_dossiers.py", label="← Aller à la gestion des dossiers",
                  icon=":material/folder_open:")
    st.stop()

etude_active = st.session_state["etudes"][active_idx]

# ─── Sidebar : logo + résumé dossier + stepper ────────────────────────────────
render_sidebar(st)
render_stepper_sidebar(st)

# ─── CSS titre d'étape compact ────────────────────────────────────────────────
st.markdown("""
<style>
.step-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 1.2rem 0;
    padding-bottom: .75rem;
    border-bottom: 1px solid #E2E8F0;
}
.step-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px; height: 28px;
    border-radius: 50%;
    background: #FDE8C2;
    color: #92600A;
    font-family: 'Space Grotesk', sans-serif;
    font-size: .8rem;
    font-weight: 700;
    flex-shrink: 0;
}
.step-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #1E293B;
    letter-spacing: -.01em;
    line-height: 1.3;
}
.step-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: .8rem;
    color: #94A3B8;
    font-weight: 400;
}
</style>
""", unsafe_allow_html=True)

def _step_header(num: int, title: str, subtitle: str = ""):
    sub_html = f'<div class="step-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'''<div class="step-header">
            <span class="step-badge">{num}</span>
            <div>
                <div class="step-title">{title}</div>
                {sub_html}
            </div>
        </div>''',
        unsafe_allow_html=True
    )



# ─── Barre de contexte compacte ───────────────────────────────────────────────
prenom     = st.session_state.get("client_prenom", "")
nom        = st.session_state.get("client_nom", "")
inst       = st.session_state.get("installateur_nom", "—")
nom_etude  = etude_active.get("nom_etude") or "Nouvelle étude"
client_str = f"{prenom} {nom}".strip() or "—"

col_info, col_btn = st.columns([7, 1])
with col_info:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;
                    padding:6px 0 6px 2px;border-bottom:1px solid #E2E8F0;
                    margin-bottom:4px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;
                         width:26px;height:26px;border-radius:6px;
                         background:#FDE8C2;flex-shrink:0;">
                <svg xmlns='http://www.w3.org/2000/svg' width='13' height='13'
                     viewBox='0 0 24 24' fill='none' stroke='#B07A2A'
                     stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
                    <path d='M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z'/>
                </svg>
            </span>
            <span style="font-family:'Space Grotesk',sans-serif;font-size:.95rem;
                         font-weight:600;color:#1E293B;letter-spacing:-.01em;">
                {nom_etude}
            </span>
            <span style="color:#CBD5E1;font-size:.85rem;">|</span>
            <span style="font-family:'Inter',sans-serif;font-size:.78rem;
                         color:#64748B;font-weight:400;">
                {client_str} &nbsp;·&nbsp; <span style="color:#94A3B8;">Diagnostiqueur :</span> {inst}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )
with col_btn:
    if st.button("← Dossiers", key="btn_back_dossiers", use_container_width=True):
        _sauvegarder()
        st.switch_page("pages/1_accueil_dossiers.py")


# ─── Numéro d'étape courant ───────────────────────────────────────────────────
if "current_step" not in st.session_state:
    st.session_state["current_step"] = 1
current_step = st.session_state["current_step"]

# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 1 — INFORMATIONS CLIENT & INSTALLATEUR
# ══════════════════════════════════════════════════════════════════════════════
if current_step == 1:
    _step_header(1, "Informations Client & Installateur", "Coordonnées, logo et photo de la maison")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.session_state["installateur_nom"] = st.text_input(
            "Nom de l'entreprise / diagnostiqueur",
            value=st.session_state.get("installateur_nom", ""),
            placeholder="ex: EcoDim Pro"
        )
        uploaded_logo = st.file_uploader("Logo personnalisé (PNG/JPG)", type=["png","jpg","jpeg"])
        if uploaded_logo:
            logo_data = uploaded_logo.read()
            st.session_state["logo_bytes"] = logo_data
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tfile.write(logo_data)
            tfile.close()
            st.session_state["logo_temp_path"] = tfile.name
            _sauvegarder()
        if st.session_state.get("logo_bytes") is not None:
            if st.button(":material/delete: Réinitialiser le logo par défaut", use_container_width=True):
                st.session_state["logo_bytes"] = None
                st.session_state["logo_temp_path"] = None
                _sauvegarder()
                st.rerun()

        uploaded_maison = st.file_uploader("Photo de la maison (PNG/JPG) [Couverture]", type=["png","jpg","jpeg"])
        if uploaded_maison:
            maison_data = uploaded_maison.read()
            st.session_state["maison_bytes"] = maison_data
            tfile_m = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tfile_m.write(maison_data)
            tfile_m.close()
            st.session_state["maison_temp_path"] = tfile_m.name
            _sauvegarder()
        if st.session_state.get("maison_bytes") is not None:
            st.image(st.session_state["maison_bytes"], caption="Aperçu photo de la maison", width=250)
            if st.button(":material/delete: Réinitialiser la photo de la maison", use_container_width=True):
                st.session_state["maison_bytes"] = None
                st.session_state["maison_temp_path"] = None
                _sauvegarder()
                st.rerun()

        st.session_state["client_societe"] = st.text_input(
            "Société du client", value=st.session_state.get("client_societe", ""),
            placeholder="ex: Famille Martin SCI"
        )

    with col_c2:
        st.session_state["client_prenom"] = st.text_input(
            "Prénom", value=st.session_state.get("client_prenom", ""),
            placeholder="ex: Albert"
        )
        st.session_state["client_nom"] = st.text_input(
            "Nom", value=st.session_state.get("client_nom", ""),
            placeholder="ex: Mercier"
        )
        client_email = st.text_input(
            "Email", value=st.session_state.get("client_email", ""),
            placeholder="ex: albert@email.com"
        )
        st.session_state["client_email"] = client_email
        if client_email and not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", client_email):
            st.warning("Format d'e-mail invalide.")
        st.session_state["client_notes"] = st.text_area(
            "Notes d'audit", value=st.session_state.get("client_notes", ""),
            placeholder="Observations, spécificités du site..."
        )

    # Navigation
    st.markdown("---")
    _, col_next = st.columns([3, 1])
    with col_next:
        if st.button("Étape 2 : Localisation →", type="primary", use_container_width=True):
            _sauvegarder()
            st.session_state["current_step"] = 2
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 2 — LOCALISATION & BÂTIMENT (GPS + Toitures)
# ══════════════════════════════════════════════════════════════════════════════
elif current_step == 2:
    _step_header(2, "Localisation & Bâtiment", "Adresse GPS, zone climatique et pans de toiture")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        adresse = st.text_input(
            "Adresse du projet", value=st.session_state.get("adresse_formatee", ""),
            placeholder="ex: 14 Avenue Verte, Bordeaux"
        )
        st.session_state["adresse_formatee"] = adresse

        if st.button(":material/search: Géocoder l'adresse"):
            with st.spinner("Géocodage…"):
                res = geocoder_adresse(adresse)
                if res:
                    st.session_state["latitude"]         = res["latitude"]
                    st.session_state["longitude"]        = res["longitude"]
                    st.session_state["adresse_formatee"] = res["adresse_formatee"]
                    st.session_state["geocode_success"]  = True
                    st.success("Adresse localisée !")
                    st.rerun()
                else:
                    st.error("Adresse introuvable.")

        st.markdown("---")
        if st.checkbox("Modifier les coordonnées GPS manuellement"):
            lat = st.number_input("Latitude (°)",  value=float(st.session_state.get("latitude", 0.0)), format="%.4f")
            lon = st.number_input("Longitude (°)", value=float(st.session_state.get("longitude", 0.0)), format="%.4f")
            st.session_state["latitude"]  = lat
            st.session_state["longitude"] = lon
        else:
            lat = float(st.session_state.get("latitude",  0.0))
            lon = float(st.session_state.get("longitude", 0.0))
            if lat != 0.0 or lon != 0.0:
                st.write(f"**Coordonnées :** {lat:.4f}°, {lon:.4f}°")
            else:
                st.info("Saisissez une adresse et cliquez sur Géocoder, ou entrez manuellement les coordonnées GPS.")

        zone_auto = detecter_zone_climatique(lat, lon)
        zones_opt = list(ZONES_CLIMATIQUES.keys())
        val_zone  = st.session_state.get("zone_climatique_choisie", zone_auto)
        if val_zone not in zones_opt:
            val_zone = zone_auto
        zone_clim = st.selectbox(
            "Zone climatique (3CL-DPE)", zones_opt,
            index=zones_opt.index(val_zone),
            format_func=lambda z: ZONES_CLIMATIQUES[z]["label"],
            help="Pré-sélectionnée selon les coordonnées GPS."
        )
        st.session_state["zone_climatique_choisie"] = zone_clim
        dh14_zone = ZONES_CLIMATIQUES[zone_clim]["dh14"]
        st.markdown(f"""
        <div class="card-neutre">
            <div style="font-size:.75rem;color:#64748B;">Références climatiques — Zone {zone_clim}</div>
            <div style="display:flex;gap:1.5rem;margin-top:.4rem;">
                <div><span style="font-size:.7rem;color:#9CA3AF;">T° moyenne</span><br>
                     <strong style="font-family:'JetBrains Mono',monospace;">{ZONES_CLIMATIQUES[zone_clim]['tmoy']:.2f} °C</strong></div>
                <div><span style="font-size:.7rem;color:#9CA3AF;">DH14 officiel</span><br>
                     <strong style="font-family:'JetBrains Mono',monospace;">{dh14_zone:,.0f} °C·h</strong></div>
            </div>
        </div>""", unsafe_allow_html=True)
        st.session_state["dh14"] = dh14_zone

    with col_m2:
        st.markdown('<div class="card-neutre"><h4>Vue Satellite du Projet</h4></div>', unsafe_allow_html=True)
        try:
            carte = folium.Map(location=[lat if lat != 0 else 46.0, lon if lon != 0 else 2.0],
                               zoom_start=18 if (lat != 0 or lon != 0) else 6, tiles=None)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri', name='Satellite'
            ).add_to(carte)
            if lat != 0 or lon != 0:
                folium.Marker([lat, lon], popup="Site", icon=folium.Icon(color='red')).add_to(carte)
            st_folium(carte, width=480, height=340, key="sat_map")
        except Exception as e:
            st.error(f"Carte : {e}")

    # ── Pans de toiture ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(":material/roofing: Pans de toiture disponibles")
    st.markdown(
        "<p style='color:#64748B;font-size:.9rem;margin-bottom:1.5rem;'>"
        "Définissez les pans de toiture pour l'installation photovoltaïque. "
        "Les obstacles seront déduits pour calculer la surface utile réelle.</p>",
        unsafe_allow_html=True
    )

    pans = st.session_state.get("pans_toiture")
    if not isinstance(pans, list):
        pans = []
        st.session_state["pans_toiture"] = pans

    orientations_map = {
        "S": {"azimut": 0.0, "label": "Sud (0°)"},
        "SE": {"azimut": -45.0, "label": "Sud-Est (-45°)"},
        "E": {"azimut": -90.0, "label": "Est (-90°)"},
        "NE": {"azimut": -135.0, "label": "Nord-Est (-135°)"},
        "N": {"azimut": 180.0, "label": "Nord (180°)"},
        "NO": {"azimut": 135.0, "label": "Nord-Ouest (135°)"},
        "O": {"azimut": 90.0, "label": "Ouest (90°)"},
        "SO": {"azimut": 45.0, "label": "Sud-Ouest (45°)"},
    }
    orientations_keys = list(orientations_map.keys())

    if not pans:
        st.info("Aucun pan de toiture défini. Cliquez sur '+ Ajouter un pan' pour commencer.")

    pans_a_supprimer = []
    for i, pan in enumerate(pans):
        with st.expander(f"Pan n°{i+1} : {pan.get('nom', 'Nouveau pan')} ({pan.get('surface_utile_m2', 0.0):.1f} m² utiles)", expanded=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                pan["nom"] = st.text_input("Nom du pan", value=pan.get("nom", f"Pan {i+1}"), key=f"pan_nom_{i}")
                type_opts = ["Toiture en pente", "Toiture terrasse"]
                t_val = pan.get("type", "Toiture en pente")
                pan["type"] = st.selectbox("Type de toiture", type_opts,
                    index=type_opts.index(t_val) if t_val in type_opts else 0, key=f"pan_type_{i}")
                pan["surface_disponible_m2"] = st.number_input(
                    "Surface disponible brute (m²)", min_value=1.0, max_value=2000.0,
                    value=float(pan.get("surface_disponible_m2", 30.0)), step=5.0, key=f"pan_surf_{i}")
                st.markdown("<div style='font-size:.85rem;font-weight:600;margin-top:.8rem;'>Obstacles</div>", unsafe_allow_html=True)
                c_chem = st.number_input("Cheminées (1m²/u.)", min_value=0, max_value=20, value=0, key=f"pan_chem_{i}")
                c_vel  = st.number_input("Velux/fenêtres toit (2m²/u.)", min_value=0, max_value=20, value=0, key=f"pan_velux_{i}")
                obstacles_m2 = (c_chem * 1.0) + (c_vel * 2.0)
                pan["surface_obstacles_m2"] = obstacles_m2
            with col_p2:
                o_val = pan.get("orientation", "S")
                if o_val not in orientations_keys:
                    o_val = "S"
                orientation_sel = st.selectbox("Orientation", orientations_keys,
                    index=orientations_keys.index(o_val),
                    format_func=lambda k: orientations_map[k]["label"], key=f"pan_ori_{i}")
                pan["orientation"] = orientation_sel
                pan["azimut"] = orientations_map[orientation_sel]["azimut"]
                default_inc = 30 if pan["type"] == "Toiture en pente" else 15
                pan["inclinaison"] = st.number_input("Inclinaison (°)", min_value=0, max_value=90,
                    value=int(pan.get("inclinaison", default_inc)), step=5, key=f"pan_inc_{i}")
                pan["ombrage_partiel"] = st.checkbox("Ombrage partiel (-10%)",
                    value=bool(pan.get("ombrage_partiel", False)), key=f"pan_ombr_{i}")
                surf_utile = max(0.0, pan["surface_disponible_m2"] - obstacles_m2)
                pan["surface_utile_m2"] = surf_utile
                st.markdown(f"""
                <div style='background:#F1F5F9;border-radius:6px;padding:.8rem;margin-top:1.5rem;text-align:center;'>
                    <span style='font-size:.75rem;color:#64748B;text-transform:uppercase;font-weight:600;'>Surface Utile Réelle</span><br>
                    <span style='font-size:1.6rem;font-family:monospace;font-weight:700;color:#1E293B;'>{surf_utile:.1f} m²</span>
                </div>""", unsafe_allow_html=True)
            if len(pans) > 1:
                if st.button(f":material/delete: Supprimer ce pan n°{i+1}", key=f"del_pan_{i}"):
                    pans_a_supprimer.append(i)

    if pans_a_supprimer:
        for idx in sorted(pans_a_supprimer, reverse=True):
            pans.pop(idx)
        st.session_state["pans_toiture"] = pans
        st.rerun()

    if st.button(":material/add: Ajouter un pan de toiture", use_container_width=True):
        pans.append({
            "nom": f"Pan n°{len(pans)+1}", "type": "Toiture en pente",
            "surface_disponible_m2": 30.0, "orientation": "S",
            "azimut": 0.0, "inclinaison": 30,
            "surface_obstacles_m2": 0.0, "surface_utile_m2": 30.0, "ombrage_partiel": False
        })
        st.session_state["pans_toiture"] = pans
        st.rerun()

    st.session_state["pans_toiture"] = pans

    # Navigation
    st.markdown("---")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← Étape 1 : Client", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 1; st.rerun()
    with col_next:
        if st.button("Étape 3 : Isolation →", type="primary", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 3; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 3 — ISOLATION & ENVELOPPE THERMIQUE
# ══════════════════════════════════════════════════════════════════════════════
elif current_step == 3:
    _step_header(3, "Isolation & Enveloppe Thermique", "Surface, coefficients U et déperditions")

    zone_clim = st.session_state.get("zone_climatique_choisie", "H2")
    dh14_zone = float(st.session_state.get("dh14", ZONES_CLIMATIQUES.get(zone_clim, {}).get("dh14", 33300.0)))

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        surface_m2 = st.number_input(
            "Surface habitable (m²)", min_value=0.0, max_value=1000.0,
            value=float(st.session_state.get("surface_m2", 0.0)), step=10.0,
            placeholder="ex: 120"
        )
        st.session_state["surface_m2"] = surface_m2

        val_umur_p = st.session_state.get("umur_periode", PERIODES_UMUR[0])
        if val_umur_p not in PERIODES_UMUR:
            val_umur_p = PERIODES_UMUR[0]
        umur_periode = st.selectbox(
            "Isolation des murs — période et type", PERIODES_UMUR,
            index=PERIODES_UMUR.index(val_umur_p),
            format_func=lambda k: UMUR_PAR_PERIODE[k]["label"]
        )
        st.session_state["umur_periode"] = umur_periode
        umur = UMUR_PAR_PERIODE[umur_periode][zone_clim]
        st.info(f"U mur retenu (zone {zone_clim}) : **{umur:.2f} W/m²K**")

        val_toit = st.session_state.get("type_toiture", TYPES_TOITURE[0])
        if val_toit not in TYPES_TOITURE:
            val_toit = TYPES_TOITURE[0]
        type_toiture = st.selectbox("Type et isolation de la toiture", TYPES_TOITURE,
            index=TYPES_TOITURE.index(val_toit))
        st.session_state["type_toiture"] = type_toiture
        uph = UPH_TOITURE[type_toiture]
        st.info(f"U toiture retenu : **{uph:.2f} W/m²K**")

        upb = UPB_PLANCHER_BAS_DEFAUT
        st.info(f"U plancher bas (officiel) : **{upb:.2f} W/m²K**")

    with col_t2:
        gv_approx = umur*(surface_m2*0.6) + uph*(surface_m2*0.3) + upb*(surface_m2*0.1)
        st.markdown(f"""
        <div class="card-neutre">
            <div style="font-size:.75rem;color:#64748B;margin-bottom:.5rem;">Coefficients U retenus — Zone {zone_clim}</div>
            <table style="width:100%;font-size:.82rem;border-collapse:collapse;">
                <tr><td style="color:#64748B;">Murs (60%)</td><td style="font-weight:600;text-align:right;">{umur:.2f} W/m²K</td></tr>
                <tr><td style="color:#64748B;">Toiture (30%)</td><td style="font-weight:600;text-align:right;">{uph:.2f} W/m²K</td></tr>
                <tr><td style="color:#64748B;">Plancher bas (10%)</td><td style="font-weight:600;text-align:right;">{upb:.2f} W/m²K</td></tr>
                <tr style="border-top:1px solid #E2E8F0;"><td style="font-weight:700;padding-top:.3rem;">GV approx.</td>
                    <td style="font-weight:700;text-align:right;font-family:'JetBrains Mono',monospace;">{gv_approx:.1f} W/K</td></tr>
            </table>
        </div>""", unsafe_allow_html=True)

        st.session_state.update(umur=umur, uph=uph, upb=upb)

        st.markdown('<div class="card-neutre"><h4>Avertissement réglementaire</h4></div>', unsafe_allow_html=True)
        st.caption(
            "⚠️ **Estimation indicative** — coefficients de référence 3CL-DPE (arrêté 31 mars 2021). "
            "Ne se substitue pas à un DPE officiel."
        )

    # Navigation
    st.markdown("---")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← Étape 2 : Localisation", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 2; st.rerun()
    with col_next:
        if st.button("Étape 4 : Électricité →", type="primary", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 4; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 4 — ÉLECTRICITÉ
# ══════════════════════════════════════════════════════════════════════════════
elif current_step == 4:
    _step_header(4, "Besoins Électriques", "Consommation annuelle hors ECS et chauffage")
    st.caption("Consommation électrique annuelle hors ECS et chauffage.")

    mode_elec_opt = ["Consommation annuelle", "Liste des appareils", "Import de fichier CSV de consommation"]
    val_mode = st.session_state.get("mode_elec", "Consommation annuelle")
    if val_mode not in mode_elec_opt:
        val_mode = "Consommation annuelle"
    mode_elec = st.radio("Mode d'évaluation", mode_elec_opt,
        index=mode_elec_opt.index(val_mode))
    st.session_state["mode_elec"] = mode_elec

    conso_horaire_csv = st.session_state.get("conso_horaire_csv")
    elec_annuel_kwh   = float(st.session_state.get("elec_annuel_kwh", 0.0))

    if mode_elec == "Consommation annuelle":
        elec_annuel_kwh = st.number_input(
            "Consommation annuelle (kWh/an)", min_value=0.0, max_value=50000.0,
            value=elec_annuel_kwh, step=100.0,
            placeholder="ex: 3500"
        )
        st.session_state["elec_annuel_kwh"] = elec_annuel_kwh
        st.session_state["conso_horaire_csv"] = None
        st.session_state["appareils_list"] = []
        if elec_annuel_kwh > 0:
            st.markdown(f"""
            <div class="card-pv">
                <div style="font-size:.9rem;color:#9CA3AF;">Consommation annuelle renseignée</div>
                <div style="font-size:1.8rem;font-family:'JetBrains Mono',monospace;font-weight:600;color:#E8A33D;">
                    {elec_annuel_kwh:,.1f} <span style="font-size:1.1rem;">kWh/an</span>
                </div>
            </div>""", unsafe_allow_html=True)

    elif mode_elec == "Liste des appareils":
        appareils_data = st.session_state.get("appareils_list") or []
        st.session_state["appareils_list"] = appareils_data

        edited_df = st.data_editor(
            pd.DataFrame(appareils_data) if appareils_data else pd.DataFrame(
                columns=["nom","puissance_w","heures_jour","jours_semaine"]
            ),
            num_rows="dynamic",
            column_config={
                "nom":           st.column_config.TextColumn("Appareil", required=True),
                "puissance_w":   st.column_config.NumberColumn("Puissance (W)", min_value=0.0, step=10.0, format="%.0f"),
                "heures_jour":   st.column_config.NumberColumn("Usage (h/jour)", min_value=0.0, max_value=24.0, step=0.1),
                "jours_semaine": st.column_config.NumberColumn("Jours/semaine", min_value=0.0, max_value=7.0, step=1.0),
            },
            key=f"appareils_editor_{st.session_state.get('active_etude_idx',0)}"
        )
        appareils_list = edited_df.to_dict(orient="records")
        st.session_state["appareils_list"] = appareils_list
        appareils_clean = [a for a in appareils_list if a.get("nom") and a.get("puissance_w") is not None]
        elec_annuel_kwh = calc_besoin_elec(appareils_clean) if appareils_clean else 0.0
        st.session_state["elec_annuel_kwh"]   = elec_annuel_kwh
        st.session_state["conso_horaire_csv"] = None
        conso_horaire_csv = None
        if elec_annuel_kwh > 0:
            st.markdown(f"""
            <div class="card-pv">
                <div style="font-size:.9rem;color:#9CA3AF;">Consommation annuelle estimée</div>
                <div style="font-size:1.8rem;font-family:'JetBrains Mono',monospace;font-weight:600;color:#E8A33D;">
                    {elec_annuel_kwh:,.1f} <span style="font-size:1.1rem;">kWh/an</span>
                </div>
            </div>""", unsafe_allow_html=True)

    else:  # CSV
        uploaded_csv = st.file_uploader("CSV de consommation (format Enedis)", type=["csv"])
        if uploaded_csv:
            try:
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
                tfile.write(uploaded_csv.read()); tfile.flush()
                elec_annuel_kwh, conso_horaire_csv = calc_besoin_elec(tfile.name)
                os.remove(tfile.name)
                st.session_state["elec_annuel_kwh"]   = elec_annuel_kwh
                st.session_state["conso_horaire_csv"] = conso_horaire_csv
                st.success("CSV importé !")
            except Exception as e:
                st.error(f"Erreur CSV : {e}")
        if conso_horaire_csv is not None:
            c1, c2 = st.columns(2)
            c1.metric("Total annuel", f"{elec_annuel_kwh:,.0f} kWh")
            c2.metric("Pas de temps", "1 heure")
            st.line_chart(conso_horaire_csv.head(168))
            st.caption("Aperçu première semaine (kWh/h)")
        else:
            st.info("Aucun fichier CSV importé.")

    # Navigation
    st.markdown("---")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← Étape 3 : Isolation", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 3; st.rerun()
    with col_next:
        if st.button("Étape 5 : ECS & Chauffage →", type="primary", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 5; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 5 — ECS & CHAUFFAGE
# ══════════════════════════════════════════════════════════════════════════════
elif current_step == 5:
    _step_header(5, "ECS & Chauffage", "Eau chaude sanitaire et besoin de chauffage")

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        st.markdown('<div class="card-thermique"><h4>Eau Chaude Sanitaire (ECS)</h4></div>', unsafe_allow_html=True)
        nb_personnes = st.number_input("Nombre d'occupants", min_value=0, max_value=20,
            value=int(st.session_state.get("nb_personnes", 0)), step=1)
        st.session_state["nb_personnes"] = nb_personnes

        scenarios_opt = list(SCENARIOS_ECS.keys())
        val_sc = st.session_state.get("scenario_ecs", scenarios_opt[0])
        if val_sc not in scenarios_opt:
            val_sc = scenarios_opt[0]
        scenario_ecs = st.selectbox("Scénario d'usage ECS", scenarios_opt,
            index=scenarios_opt.index(val_sc),
            help="Valeur réglementaire DPE : 56 L/j/pers à 40°C (arrêté 31 mars 2021).")
        st.session_state["scenario_ecs"] = scenario_ecs

        litres_val = SCENARIOS_ECS[scenario_ecs]
        if litres_val is None:
            litres_par_pers = st.number_input("Litres/jour/personne", min_value=0.0, max_value=200.0,
                value=float(st.session_state.get("litres_par_pers", 0.0)), step=5.0)
            t_eau_froide = st.number_input("T° eau froide (°C)", min_value=0.0, max_value=25.0,
                value=float(st.session_state.get("t_eau_froide", 0.0)), step=1.0)
            t_eau_chaude = st.number_input("T° eau chaude cible (°C)", min_value=0.0, max_value=85.0,
                value=float(st.session_state.get("t_eau_chaude", 0.0)), step=1.0)
        else:
            litres_par_pers = litres_val
            t_eau_froide    = ECS_TEMP_FROIDE_REFERENCE
            t_eau_chaude    = ECS_TEMP_CHAUDE_CONVENTIONNEL
            st.info(f"**{scenario_ecs}** : {int(litres_par_pers)} L/j/pers à {int(t_eau_chaude)}°C")

        st.session_state.update(litres_par_pers=litres_par_pers, t_eau_froide=t_eau_froide, t_eau_chaude=t_eau_chaude)

        if nb_personnes > 0:
            ecs_annuel_kwh = calc_besoin_ecs(nb_personnes, litres_par_pers, t_eau_froide, t_eau_chaude)
            st.session_state["ecs_annuel_kwh"] = ecs_annuel_kwh
            st.markdown(f"""
            <div class="card-thermique">
                <div style="font-size:.9rem;color:#9CA3AF;">Besoin thermique ECS annuel</div>
                <div style="font-size:1.8rem;font-family:'JetBrains Mono',monospace;font-weight:600;color:#3DBFAE;">
                    {ecs_annuel_kwh:,.1f} <span style="font-size:1.1rem;">kWh/an</span>
                </div>
            </div>""", unsafe_allow_html=True)

    with col_e2:
        st.markdown('<div class="card-thermique"><h4>Chauffage Principal</h4></div>', unsafe_allow_html=True)
        inclure_chauffage = st.toggle("Activer le calcul du chauffage",
            value=st.session_state.get("inclure_chauffage", False))
        st.session_state["inclure_chauffage"] = inclure_chauffage

        surface_m2 = float(st.session_state.get("surface_m2", 0.0))
        umur_val   = float(st.session_state.get("umur",  2.50))
        uph_val    = float(st.session_state.get("uph",   0.43))
        upb_val    = float(st.session_state.get("upb",   UPB_PLANCHER_BAS_DEFAUT))
        dh14_val   = float(st.session_state.get("dh14",  33_300.0))
        zone_ch    = st.session_state.get("zone_climatique_choisie", "H2")

        st.markdown(f"""
        <div class="card-neutre">
            <div style="font-size:.75rem;color:#64748B;margin-bottom:.4rem;">Paramètres thermiques actifs</div>
            <span style="font-size:.8rem;color:#64748B;">Surface : </span><strong>{surface_m2:.0f} m²</strong> &nbsp;
            <span style="font-size:.8rem;color:#64748B;">Zone : </span><strong>{zone_ch}</strong> &nbsp;
            <span style="font-size:.8rem;color:#64748B;">DH14 : </span><strong style="font-family:'JetBrains Mono',monospace;">{dh14_val:,.0f} °C·h</strong>
        </div>""", unsafe_allow_html=True)

        if inclure_chauffage and surface_m2 > 0:
            chauffage_kwh = calc_besoin_chauffage(surface_m2=surface_m2,
                umur=umur_val, uph=uph_val, upb=upb_val, dh14=dh14_val)
            st.session_state["chauffage_annuel_kwh"] = chauffage_kwh
            st.markdown(f"""
            <div class="card-thermique">
                <div style="font-size:.9rem;color:#9CA3AF;">Besoin thermique chauffage annuel</div>
                <div style="font-size:1.8rem;font-family:'JetBrains Mono',monospace;font-weight:600;color:#3DBFAE;">
                    {chauffage_kwh:,.1f} <span style="font-size:1.1rem;">kWh/an</span>
                </div>
            </div>""", unsafe_allow_html=True)
            st.caption("⚠️ Estimation 3CL-DPE simplifiée — ne se substitue pas à un DPE officiel.")
        elif inclure_chauffage:
            st.warning("Renseignez la surface habitable (Étape 3) pour calculer le besoin de chauffage.")
        else:
            st.session_state["chauffage_annuel_kwh"] = 0.0

    # Navigation
    st.markdown("---")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← Étape 4 : Électricité", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 4; st.rerun()
    with col_next:
        if st.button("Étape 6 : Solaire →", type="primary", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 6; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 6 — SOLAIRE & BATTERIE
# ══════════════════════════════════════════════════════════════════════════════
elif current_step == 6:
    _step_header(6, "Équipements Solaire & Batterie", "Panneaux, onduleur, thermique, batterie et câblage")
    st.markdown(
        "<p style='color:#64748B;font-size:.9rem;margin-bottom:1.5rem;'>"
        "Sélectionnez le matériel PV et thermique dans le catalogue. Le nombre maximum de panneaux "
        "est calculé selon la surface utile des pans définis à l'Étape 2.</p>",
        unsafe_allow_html=True
    )

    panneaux_cat  = charger_catalogue("panneaux")
    onduleurs_cat = charger_catalogue("onduleurs")
    batteries_cat = charger_catalogue("batteries")

    col_s1, col_s2 = st.columns(2)
    total_panneaux_retenus = 0

    with col_s1:
        st.markdown('<div class="card-pv"><h4>1. Panneau Photovoltaïque</h4></div>', unsafe_allow_html=True)
        if not panneaux_cat:
            st.error("Catalogue panneaux.json introuvable ou vide.")
            panneau_choisi = None
        else:
            pan_opts_ids = [p["id"] for p in panneaux_cat]
            pan_labels   = [f"{p['nom']} — {p['puissance_wc']}Wc ({p['prix_unitaire_eur']:.0f}€)" for p in panneaux_cat]
            p_sel_id = st.session_state.get("panneau_choisi_id")
            if p_sel_id not in pan_opts_ids:
                p_sel_id = pan_opts_ids[0]
            panneau_choisi_id = st.selectbox("Modèle de panneau", options=pan_opts_ids,
                index=pan_opts_ids.index(p_sel_id),
                format_func=lambda x: pan_labels[pan_opts_ids.index(x)], key="sel_panneau")
            st.session_state["panneau_choisi_id"] = panneau_choisi_id
            panneau_choisi = panneaux_cat[pan_opts_ids.index(panneau_choisi_id)]
            st.caption(f"Dimensions : {panneau_choisi['longueur_m']}m × {panneau_choisi['largeur_m']}m | Rendement : {panneau_choisi['rendement_pct']}%")

        st.markdown("<div style='font-weight:600;margin-top:1rem;margin-bottom:.5rem;'>Disposition des panneaux par pan</div>", unsafe_allow_html=True)
        pans = st.session_state.get("pans_toiture", [])
        panneaux_par_pan = st.session_state.get("panneaux_par_pan", {})
        if not isinstance(panneaux_par_pan, dict):
            panneaux_par_pan = {}

        if not pans:
            st.warning("Définissez d'abord des pans de toiture à l'Étape 2.")
        elif panneau_choisi:
            for idx_pan, pan in enumerate(pans):
                nb_max = calculer_nb_panneaux_max(pan["surface_utile_m2"], panneau_choisi)
                key_str = str(idx_pan)
                val_prec = panneaux_par_pan.get(key_str, nb_max)
                if not isinstance(val_prec, int) or val_prec > nb_max:
                    val_prec = nb_max
                nb_retenus = st.slider(
                    f"Pan n°{idx_pan+1} ({pan['nom']}) — Max {nb_max} panneaux",
                    min_value=0, max_value=max(nb_max, 1), value=val_prec, key=f"slider_pan_{idx_pan}")
                panneaux_par_pan[key_str] = nb_retenus
                total_panneaux_retenus += nb_retenus
                p_pan_kwc = puissance_totale_kwc(nb_retenus, panneau_choisi)
                st.caption(f"Puissance sur ce pan : **{p_pan_kwc:.2f} kWc** ({nb_retenus} panneaux)")
            st.session_state["panneaux_par_pan"] = panneaux_par_pan
            kwp_tot_pv = puissance_totale_kwc(total_panneaux_retenus, panneau_choisi)
            st.session_state["kwp_pvgis"] = kwp_tot_pv
            if total_panneaux_retenus > 0:
                st.success(f"Installation totale : **{total_panneaux_retenus} panneaux** — **{kwp_tot_pv:.2f} kWc**")

        st.markdown('<div class="card-pv"><h4>2. Onduleur</h4></div>', unsafe_allow_html=True)
        if not onduleurs_cat:
            st.error("Catalogue onduleurs.json introuvable.")
            onduleur_choisi = None
        elif panneau_choisi:
            kwp_tot_pv = st.session_state.get("kwp_pvgis", 0.0)
            ond_compatibles = []
            for ond in onduleurs_cat:
                if ond["type"] == "micro":
                    ond_compatibles.append(ond)
                elif kwp_tot_pv > 0 and 0.70 * kwp_tot_pv <= ond["puissance_kw"] <= 1.30 * kwp_tot_pv:
                    ond_compatibles.append(ond)
            if not ond_compatibles:
                ond_compatibles = onduleurs_cat
            ond_ids    = [o["id"] for o in ond_compatibles]
            ond_labels = [f"{o['nom']} ({o['puissance_kw']} kW, {o['prix_eur']:.0f}€)" for o in ond_compatibles]
            ond_sel_id = st.session_state.get("onduleur_choisi_id")
            if ond_sel_id not in ond_ids:
                ond_sel_id = ond_ids[0]
            onduleur_choisi_id = st.selectbox("Onduleur compatible", options=ond_ids,
                index=ond_ids.index(ond_sel_id),
                format_func=lambda x: ond_labels[ond_ids.index(x)], key="sel_onduleur")
            st.session_state["onduleur_choisi_id"] = onduleur_choisi_id

    with col_s2:
        st.markdown('<div class="card-thermique"><h4>Solaire Thermique (ECS)</h4></div>', unsafe_allow_html=True)
        surface_th   = st.number_input("Surface capteurs (m²)", min_value=0.0, max_value=50.0,
            value=float(st.session_state.get("surface_th", 0.0)), step=0.5)
        rendement_th = st.number_input("Rendement optique moyen", min_value=0.0, max_value=0.90,
            value=float(st.session_state.get("rendement_th", 0.0)), step=0.05)
        st.session_state.update(surface_th=surface_th, rendement_th=rendement_th)

        st.markdown("---")
        st.markdown('<div class="card-pv"><h4>3. Batterie de Stockage</h4></div>', unsafe_allow_html=True)
        inclure_bat = st.toggle("Activer la batterie", value=st.session_state.get("inclure_batterie", False))
        st.session_state["inclure_batterie"] = inclure_bat
        if inclure_bat and batteries_cat:
            bat_opts_ids = [b["id"] for b in batteries_cat]
            bat_labels   = [f"{b['nom']} — {b['capacite_kwh']} kWh ({b['prix_eur']:.0f}€)" for b in batteries_cat]
            b_sel_id = st.session_state.get("batterie_choisie_id")
            if b_sel_id not in bat_opts_ids:
                b_sel_id = bat_opts_ids[0]
            batterie_choisie_id = st.selectbox("Modèle de batterie", options=bat_opts_ids,
                index=bat_opts_ids.index(b_sel_id),
                format_func=lambda x: bat_labels[bat_opts_ids.index(x)], key="sel_batterie")
            st.session_state["batterie_choisie_id"] = batterie_choisie_id
            batterie_choisie = batteries_cat[bat_opts_ids.index(batterie_choisie_id)]
            st.session_state["capacite_bat"] = float(batterie_choisie["capacite_kwh"])
            st.session_state["rendement_bat"] = float(batterie_choisie["rendement_pct"] / 100.0)
            st.caption(f"Technologie : {batterie_choisie['technologie']} | Cycles : {batterie_choisie['cycles_garantis']}")
        else:
            st.session_state.update(capacite_bat=0.0, rendement_bat=0.0)

        st.markdown("---")
        st.markdown('<div class="card-neutre"><h4>4. Câblage & Conformité NF C 15-100</h4></div>', unsafe_allow_html=True)
        dist_toit = st.number_input("Longueur câble toit-onduleur (m)", min_value=0.0, max_value=150.0,
            value=float(st.session_state.get("distance_toit_onduleur", 0.0)), step=5.0, key="dist_toit_ond")
        st.session_state["distance_toit_onduleur"] = dist_toit

        if dist_toit > 0 and total_panneaux_retenus > 0:
            courant_dc = 12.5
            section_dc = estimer_section_cable(courant_a=courant_dc, longueur_m=dist_toit, chute_tension_max_pct=3.0, tension_v=400.0)
            metrages = estimer_metrage_cablage(nb_panneaux=total_panneaux_retenus, distance_toit_onduleur_m=dist_toit)
            st.markdown(f"""
            <div style="background:#FFF;padding:.8rem;border:1px solid #E2E8F0;border-radius:6px;font-size:.82rem;">
                <table style="width:100%;">
                    <tr><td style="color:#64748B;">Section câble DC</td>
                        <td style="text-align:right;font-weight:600;color:#E8A33D;">{section_dc} mm²</td></tr>
                    <tr><td style="color:#64748B;">Câble DC estimé</td>
                        <td style="text-align:right;font-weight:600;">{metrages['cable_dc_m']} m</td></tr>
                    <tr><td style="color:#64748B;">Câble AC estimé</td>
                        <td style="text-align:right;font-weight:600;">{metrages['cable_ac_m']} m</td></tr>
                    <tr><td style="color:#64748B;">Câble Terre estimé</td>
                        <td style="text-align:right;font-weight:600;">{metrages['cable_terre_m']} m</td></tr>
                </table>
                <div style="font-size:.7rem;color:#94A3B8;margin-top:.4rem;">*Indicatif NF C 15-100 — à valider sur chantier.</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="card-pv"><h4>Paramètres de Raccordement Réseau</h4></div>', unsafe_allow_html=True)
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        net_opts = ["230V monophasé","400V triphasé (230V L-N / 400V L-L)"]
        val_net  = st.session_state.get("reseau_type","230V monophasé")
        reseau_type = st.selectbox("Type raccordement", net_opts, index=net_opts.index(val_net) if val_net in net_opts else 0)
        cos_phi = st.number_input("Facteur de puissance (cos φ)", min_value=0.80, max_value=1.00,
            value=float(st.session_state.get("cos_phi", 1.0)), step=0.01)
        st.session_state.update(reseau_type=reseau_type, cos_phi=cos_phi)
    with col_n2:
        inj_active = st.toggle("Limite d'injection réseau", value=st.session_state.get("injection_limite_active", False))
        st.session_state["injection_limite_active"] = inj_active
        inj_kw = st.number_input("Puissance max injectée (kW)", min_value=0.0, max_value=250.0,
            value=float(st.session_state.get("injection_limite_kw", 0.0) or 0.0), step=0.5) if inj_active else None
        st.session_state["injection_limite_kw"] = inj_kw

    # Navigation
    st.markdown("---")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← Étape 5 : ECS & Chauffage", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 5; st.rerun()
    with col_next:
        if st.button("Étape 7 : Économie →", type="primary", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 7; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 7 — ÉCONOMIE
# ══════════════════════════════════════════════════════════════════════════════
elif current_step == 7:
    _step_header(7, "Hypothèses Économiques", "Tarifs énergie, CAPEX détaillé et financement")

    col_eco1, col_eco2 = st.columns(2)
    with col_eco1:
        st.markdown('<div class="card-neutre"><h4>Tarifs Énergie & Durée</h4></div>', unsafe_allow_html=True)
        prix_reseau  = st.number_input("Prix achat réseau (€/kWh)", min_value=0.0, max_value=1.0,
            value=float(st.session_state.get("prix_reseau", 0.0)), step=0.01)
        tarif_rachat = st.number_input("Tarif rachat surplus (€/kWh)", min_value=0.00, max_value=0.5,
            value=float(st.session_state.get("tarif_rachat", 0.0)), step=0.01)
        duree_fin    = st.number_input("Durée exploitation (ans)", min_value=0, max_value=40,
            value=int(st.session_state.get("duree_financement", 0)), step=5)
        taux_act_pct = float(st.session_state.get("taux_act", 0.0)) * 100
        taux_act     = st.number_input("Taux actualisation (%)", min_value=0.0, max_value=10.0,
            value=taux_act_pct, step=0.5) / 100
        st.session_state.update(prix_reseau=prix_reseau, tarif_rachat=tarif_rachat,
                                 duree_financement=duree_fin, taux_act=taux_act)

    with col_eco2:
        st.markdown('<div class="card-neutre"><h4>CAPEX Détaillé (Matériel & Pose)</h4></div>', unsafe_allow_html=True)
        p_cat = charger_catalogue("panneaux")
        o_cat = charger_catalogue("onduleurs")
        b_cat = charger_catalogue("batteries")
        p_choisi = next((p for p in p_cat if p["id"] == st.session_state.get("panneau_choisi_id")), None) if p_cat else None
        o_choisi = next((o for o in o_cat if o["id"] == st.session_state.get("onduleur_choisi_id")), None) if o_cat else None
        inclure_bat = st.session_state.get("inclure_batterie", False)
        b_choisi = next((b for b in b_cat if b["id"] == st.session_state.get("batterie_choisie_id")), None) if b_cat and inclure_bat else None
        panneaux_par_pan = st.session_state.get("panneaux_par_pan", {})
        nb_tot_pv = sum(panneaux_par_pan.values()) if isinstance(panneaux_par_pan, dict) else 0

        forfait_pose = st.number_input("Forfait Pose, Fixations & Main d'œuvre (€)",
            min_value=0.0, max_value=25000.0,
            value=float(st.session_state.get("forfait_pose_installation", 0.0)), step=100.0,
            key="forfait_pose_install")
        st.session_state["forfait_pose_installation"] = forfait_pose

        prix_th_m2 = st.number_input("Coût Solaire Thermique (€/m²)", min_value=0.0, max_value=5000.0,
            value=float(st.session_state.get("prix_th_m2", 0.0)), step=50.0)
        st.session_state["prix_th_m2"] = prix_th_m2

        cost_panels  = nb_tot_pv * (p_choisi["prix_unitaire_eur"] if p_choisi else 0.0)
        cost_inverter = o_choisi["prix_eur"] if o_choisi else 0.0
        cost_battery  = b_choisi["prix_eur"] if b_choisi else 0.0
        surf_th = float(st.session_state.get("surface_th", 0.0))
        capex_pv_calc  = cost_panels + cost_inverter + forfait_pose
        capex_th_calc  = surf_th * prix_th_m2
        capex_bat_calc = cost_battery
        capex_tot      = capex_pv_calc + capex_th_calc + capex_bat_calc

        st.session_state["prix_pv_kwp"]  = capex_pv_calc / max(0.1, st.session_state.get("kwp_pvgis", 0.1))
        st.session_state["prix_bat_kwh"] = capex_bat_calc / max(1.0, st.session_state.get("capacite_bat", 1.0)) if inclure_bat else 0.0
        st.session_state.update(capex_pv_calc=capex_pv_calc, capex_th_calc=capex_th_calc,
                                 capex_bat_calc=capex_bat_calc, capex_total=capex_tot)

        st.markdown(f"""
        <div class="card-neutre">
            <div style="font-size:.75rem;color:#64748B;margin-bottom:.4rem;">CAPEX Détaillé Estimé</div>
            <table style="width:100%;font-size:.82rem;border-collapse:collapse;">
                <tr><td style="color:#64748B;">Panneaux PV ({nb_tot_pv} u.)</td><td style="text-align:right;font-weight:600;">{cost_panels:,.0f} €</td></tr>
                <tr><td style="color:#64748B;">Onduleur ({o_choisi['nom'] if o_choisi else 'aucun'})</td><td style="text-align:right;font-weight:600;">{cost_inverter:,.0f} €</td></tr>
                <tr><td style="color:#64748B;">Pose, fixations & câblage</td><td style="text-align:right;font-weight:600;">{forfait_pose:,.0f} €</td></tr>
                <tr style="border-bottom:1px solid #E2E8F0;"><td style="color:#1E3A8A;font-weight:500;">Sous-total PV</td><td style="text-align:right;font-weight:600;color:#1E3A8A;">{capex_pv_calc:,.0f} €</td></tr>
                <tr><td style="color:#64748B;padding-top:.3rem;">Solaire Thermique ({surf_th:.1f} m²)</td><td style="text-align:right;font-weight:600;padding-top:.3rem;">{capex_th_calc:,.0f} €</td></tr>
                <tr><td style="color:#64748B;">Batterie ({b_choisi['nom'] if b_choisi else 'aucune'})</td><td style="text-align:right;font-weight:600;">{capex_bat_calc:,.0f} €</td></tr>
                <tr style="border-top:1px solid #E2E8F0;"><td style="font-weight:700;padding-top:.3rem;font-size:.9rem;">Total CAPEX</td>
                    <td style="font-weight:700;text-align:right;font-family:'JetBrains Mono',monospace;color:#E8A33D;font-size:1.15rem;">{capex_tot:,.0f} €</td></tr>
            </table>
        </div>""", unsafe_allow_html=True)

    # Navigation
    st.markdown("---")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← Étape 6 : Solaire", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 6; st.rerun()
    with col_next:
        if st.button("Étape 8 : Résultats →", type="primary", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 8; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 8 — RÉSULTATS & RAPPORT
# ══════════════════════════════════════════════════════════════════════════════
elif current_step == 8:
    _step_header(8, "Synthèse de Simulation & Rapport", "KPI, jauges, bilan financier et export PDF")

    lat_r    = float(st.session_state.get("latitude", 0.0))
    lon_r    = float(st.session_state.get("longitude", 0.0))
    kwp_r    = float(st.session_state.get("kwp_pvgis", 0.0))
    inc_r    = int(st.session_state.get("inclinaison_pv", 0))
    az_r     = int(st.session_state.get("azimut_pv", 0))
    pr_r     = float(st.session_state.get("pr_pv", 0.85))
    s_th_r   = float(st.session_state.get("surface_th", 0.0))
    rend_th  = float(st.session_state.get("rendement_th", 0.0))
    inc_bat  = st.session_state.get("inclure_batterie", False)
    cap_bat  = float(st.session_state.get("capacite_bat", 0.0))
    rend_bat = float(st.session_state.get("rendement_bat", 0.85))
    nb_pers  = int(st.session_state.get("nb_personnes", 0))
    litres_r = float(st.session_state.get("litres_par_pers", 0.0))
    tf_r     = float(st.session_state.get("t_eau_froide", 12.0))
    tc_r     = float(st.session_state.get("t_eau_chaude", 40.0))
    elec_r   = float(st.session_state.get("elec_annuel_kwh", 0.0))
    csv_r    = st.session_state.get("conso_horaire_csv")
    surf_r   = float(st.session_state.get("surface_m2", 0.0))
    umur_r   = float(st.session_state.get("umur",  2.50))
    uph_r    = float(st.session_state.get("uph",   0.43))
    upb_r    = float(st.session_state.get("upb",   UPB_PLANCHER_BAS_DEFAUT))
    dh14_r   = float(st.session_state.get("dh14",  33_300.0))
    inc_ch   = st.session_state.get("inclure_chauffage", False)
    pr_res   = float(st.session_state.get("prix_reseau", 0.0))
    tr_res   = float(st.session_state.get("tarif_rachat", 0.0))
    dur_res  = int(st.session_state.get("duree_financement", 20))
    taux_r   = float(st.session_state.get("taux_act", 0.03))
    reseau_r = st.session_state.get("reseau_type","230V monophasé")
    cos_r    = float(st.session_state.get("cos_phi", 1.0))
    inj_act  = st.session_state.get("injection_limite_active", False)
    inj_kw   = st.session_state.get("injection_limite_kw")
    client_n = f"{st.session_state.get('client_prenom','')} {st.session_state.get('client_nom','')}".strip()

    # Vérification minimale
    if kwp_r == 0.0 and elec_r == 0.0:
        st.warning("⚠️ Données insuffisantes pour calculer les résultats. Renseignez au minimum les étapes Électricité et Solaire.")
        st.markdown("---")
        if st.button("← Étape 7 : Économie", use_container_width=True):
            st.session_state["current_step"] = 7; st.rerun()
        st.stop()

    with st.spinner("Calculs & simulation multi-orientations en cours…"):
        p_cat_res = charger_catalogue("panneaux")
        p_choisi_res = next((p for p in p_cat_res if p["id"] == st.session_state.get("panneau_choisi_id")), None) if p_cat_res else None
        p_wc_res = p_choisi_res["puissance_wc"] if p_choisi_res else 425.0

        pans_res = st.session_state.get("pans_toiture", [])
        panneaux_par_pan_res = st.session_state.get("panneaux_par_pan", {})

        prod_pv_m = pd.Series(0.0, index=range(1, 13))
        has_panels = False
        max_pan_idx = 0
        max_pan_count = -1

        for i, pan in enumerate(pans_res):
            nb_p_pan = panneaux_par_pan_res.get(str(i), 0) if isinstance(panneaux_par_pan_res, dict) else 0
            if nb_p_pan > max_pan_count:
                max_pan_count = nb_p_pan; max_pan_idx = i
            if nb_p_pan > 0:
                has_panels = True
                kwp_pan = nb_p_pan * p_wc_res / 1000.0
                prod_m = production_pv_mensuelle(lat_r, lon_r, kwp_pan, pan["inclinaison"], pan["azimut"], pr_r)
                if pan.get("ombrage_partiel"):
                    prod_m = prod_m * 0.9
                prod_pv_m = prod_pv_m + prod_m

        if not has_panels and kwp_r > 0:
            prod_pv_m = production_pv_mensuelle(lat_r, lon_r, kwp_r, inc_r, az_r, pr_r)
        prod_pv_an = float(prod_pv_m.sum())

        if pans_res:
            pan_princ = pans_res[max_pan_idx]
            pvgis_data = recuperer_irradiation_pvgis(lat_r, lon_r, pan_princ["inclinaison"], pan_princ["azimut"])
        else:
            pvgis_data = recuperer_irradiation_pvgis(lat_r, lon_r, inc_r, az_r)
        irrad_an    = sum(m["H(i)_d"] * DAYS_IN_MONTH[m["month"]] for m in pvgis_data["outputs"]["monthly"])
        station_str = pvgis_data.get("inputs",{}).get("meteo_data",{}).get("radiation_db","PVGIS-SARAH2")
        st.session_state["station_meteo"] = station_str

        ecs_r_kwh   = calc_besoin_ecs(nb_pers, litres_r, tf_r, tc_r) if nb_pers > 0 else 0.0
        chauf_r_kwh = calc_besoin_chauffage(surf_r, umur_r, uph_r, upb_r, dh14_r) if inc_ch and surf_r > 0 else 0.0

        vol_ballon = dimensionner_ballon(nb_pers * litres_r) if nb_pers > 0 else 0.0
        bilan_th   = couverture_ecs(s_th_r, rend_th, ecs_r_kwh, irrad_an) if s_th_r > 0 and ecs_r_kwh > 0 else {"taux_couverture": 0.0}

        if csv_r is not None:
            bilan_pv = calc_autoconsommation(prod_pv_m, csv_r)
        else:
            elec_mensuelle = pd.Series([elec_r / 12.0] * 12, index=range(1, 13))
            bilan_pv = calc_autoconsommation(prod_pv_m, elec_mensuelle)

        if inc_bat and cap_bat > 0:
            if csv_r is not None:
                heures = csv_r.index.hour
                soleil = np.where((heures >= 7) & (heures <= 19), np.sin((heures-7)/12*np.pi), 0.0)
                s_sum  = soleil.sum()
                prod_h = pd.Series(prod_pv_an*(soleil/s_sum) if s_sum > 0 else soleil, index=csv_r.index)
                gain_b = gain_autoconsommation_avec_batterie(prod_h, csv_r, cap_bat, rend_bat)
            else:
                gain_b = gain_autoconsommation_avec_batterie(prod_pv_m, elec_r, cap_bat, rend_bat)
            auto_sans = float(bilan_pv.get("energie_autoconsommee_kwh", 0.0))
            gain_kwh  = float(gain_b.get("gain_kwh", 0.0))
            total_autoconso = auto_sans + gain_kwh
            taux_auto_c = (total_autoconso / prod_pv_an * 100.0) if prod_pv_an > 0 else 0.0
            taux_auto_s = (total_autoconso / elec_r * 100.0) if elec_r > 0 else 0.0
            surplus = max(0.0, prod_pv_an - total_autoconso)
            bilan_pv_bat = {
                "autoconsommation_directe": total_autoconso,
                "taux_autoconsommation":    min(100.0, taux_auto_c),
                "taux_autosuffisance":      min(100.0, taux_auto_s),
                "taux_autonomie":           min(100.0, taux_auto_s),
                "surplus_kwh":              surplus,
                "surplus_injecte":          surplus,
                "energie_autoconsommee_kwh": total_autoconso
            }
        else:
            bilan_pv_bat = {
                "autoconsommation_directe": float(bilan_pv.get("energie_autoconsommee_kwh", 0.0)),
                "taux_autoconsommation":    float(bilan_pv.get("taux_autoconsommation", 0.0)) * 100.0,
                "taux_autosuffisance":      float(bilan_pv.get("taux_autosuffisance", 0.0)) * 100.0,
                "taux_autonomie":           float(bilan_pv.get("taux_autonomie", 0.0)) * 100.0,
                "surplus_kwh":              float(bilan_pv.get("surplus_kwh", 0.0)),
                "surplus_injecte":          float(bilan_pv.get("surplus_kwh", 0.0)),
                "energie_autoconsommee_kwh": float(bilan_pv.get("energie_autoconsommee_kwh", 0.0))
            }

        capex_pv_r  = float(st.session_state.get("capex_pv_calc", 0.0))
        capex_th_r  = float(st.session_state.get("capex_th_calc", 0.0))
        capex_bat_r = float(st.session_state.get("capex_bat_calc", 0.0))
        capex_tot_r = float(st.session_state.get("capex_total", capex_pv_r + capex_th_r + capex_bat_r))

        auto_kwh    = prod_pv_an * (bilan_pv_bat.get("taux_autoconsommation", 0.0) / 100.0)
        surplus_kwh = max(0.0, prod_pv_an - auto_kwh)
        economies_elec = economies_annuelles(auto_kwh, pr_res, surplus_kwh, tr_res)
        taux_couv = bilan_th.get("taux_couverture", 0.0) if isinstance(bilan_th, dict) else float(bilan_th)
        economies_th = (ecs_r_kwh * taux_couv) * pr_res
        eco_an_r = economies_elec + economies_th
        pb_r     = payback_simple(capex_tot_r, eco_an_r) if eco_an_r > 0 and capex_tot_r > 0 else None
        van_r    = van(capex_tot_r, eco_an_r, duree_ans=dur_res, taux_actualisation=taux_r) if capex_tot_r > 0 else 0.0

    # ── KPI ──────────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(":material/wb_sunny: Production PV",    f"{prod_pv_an:,.0f} kWh/an")
    k2.metric(":material/bolt: Conso électrique",      f"{elec_r:,.0f} kWh/an")
    k3.metric(":material/local_fire_department: ECS", f"{ecs_r_kwh:,.0f} kWh/an")
    k4.metric(":material/payments: Économies",         f"{eco_an_r:,.0f} €/an")
    k5.metric(":material/schedule: Retour invest.",    f"{pb_r:.1f} ans" if pb_r else "—")

    st.markdown("---")

    # ── Jauges ───────────────────────────────────────────────────────────────
    jg1, jg2, jg3 = st.columns(3)
    with jg1:
        st.plotly_chart(creer_jauge(go, float(bilan_pv_bat.get("taux_autoconsommation",0)),
            "Taux d'Autoconsommation PV", "#E8A33D"), use_container_width=True)
    with jg2:
        st.plotly_chart(creer_jauge(go, float(bilan_pv_bat.get("taux_autosuffisance",0)),
            "Taux d'Autosuffisance", "#3DBFAE"), use_container_width=True)
    with jg3:
        couv_ecs_r = float(bilan_th.get("taux_couverture",0)) if isinstance(bilan_th, dict) else float(bilan_th)
        if couv_ecs_r <= 1.0:
            couv_ecs_r *= 100.0
        st.plotly_chart(creer_jauge(go, couv_ecs_r,
            "Couverture ECS Solaire Thermique", "#64748B"), use_container_width=True)

    st.markdown("---")

    # ── Bilan financier ───────────────────────────────────────────────────────
    st.markdown('<div class="card-neutre"><h4>Bilan Financier</h4></div>', unsafe_allow_html=True)
    bf1, bf2, bf3, bf4 = st.columns(4)
    bf1.metric("CAPEX total",    f"{capex_tot_r:,.0f} €")
    bf2.metric("Économies/an",   f"{eco_an_r:,.0f} €/an")
    bf3.metric("VAN actualisée", f"{van_r:,.0f} €")
    bf4.metric("TRI approx.",    f"{((eco_an_r/capex_tot_r)*100):.1f} %/an" if capex_tot_r > 0 else "—")

    # ── Production mensuelle ──────────────────────────────────────────────────
    st.markdown("---")
    mois = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]
    fig_b = go.Figure()
    fig_b.add_trace(go.Bar(x=mois, y=list(prod_pv_m), marker_color="#E8A33D", name="Production PV (kWh)"))
    fig_b.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8FAFC",
        font=dict(family="Inter"), height=300, margin=dict(l=10,r=10,t=10,b=10),
        title="Production PV mensuelle (kWh)")
    st.plotly_chart(fig_b, use_container_width=True)

    # ── Injection réseau et surplus ───────────────────────────────────────────
    surplus_injecte_m = [max(0.0, float(prod_pv_m[m]) - (elec_r/12.0)) for m in range(1,13)]
    if any(v > 0 for v in surplus_injecte_m):
        st.markdown("---")
        st.markdown('<div class="card-pv"><h4>Injection sur le Réseau & Surplus</h4></div>', unsafe_allow_html=True)
        c_inj1, c_inj2 = st.columns(2)
        with c_inj1:
            surplus_kwh_total = sum(surplus_injecte_m)
            rev_injection = surplus_kwh_total * tr_res if tr_res > 0 else 0.0
            st.metric("Surplus annuel injecté", f"{surplus_kwh_total:,.0f} kWh/an")
            if rev_injection > 0:
                st.metric("Revenu injection estimé", f"{rev_injection:,.0f} €/an")
        with c_inj2:
            fig_inj = go.Figure()
            fig_inj.add_trace(go.Bar(x=mois, y=surplus_injecte_m, marker_color="#3DBFAE", name="Surplus injecté (kWh)"))
            fig_inj.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8FAFC",
                font=dict(family="Inter"), height=250, margin=dict(l=10,r=10,t=30,b=10),
                title="Surplus mensuel injecté (kWh)")
            st.plotly_chart(fig_inj, use_container_width=True)

    # ── Dimensionnement thermique ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="card-thermique"><h4>Dimensionnement Thermique</h4></div>', unsafe_allow_html=True)
    dt1, dt2, dt3, dt4 = st.columns(4)
    dt1.metric("Volume ballon ECS",      f"{vol_ballon:.0f} L")
    dt2.metric("Surface capteurs",       f"{s_th_r:.1f} m²")
    dt3.metric("Couverture solaire ECS", f"{couv_ecs_r:.1f} %")
    dt4.metric("Besoin chauffage",       f"{chauf_r_kwh:,.0f} kWh/an")

    st.markdown("---")

    # ── Rapport PDF ───────────────────────────────────────────────────────────
    st.markdown('<div class="card-neutre"><h4>Exporter le Rapport PDF</h4></div>', unsafe_allow_html=True)

    DISCLAIMER_DPE = (
        "Estimation indicative basée sur les coefficients de référence de la méthode 3CL-DPE "
        "(arrêté du 31 mars 2021). Cette simulation ne constitue pas un diagnostic de performance "
        "énergétique (DPE) réglementaire et ne peut se substituer à un diagnostic officiel réalisé "
        "par un diagnostiqueur certifié."
    )

    p_cat_pdf = charger_catalogue("panneaux")
    o_cat_pdf = charger_catalogue("onduleurs")
    b_cat_pdf = charger_catalogue("batteries")
    p_choisi_pdf = next((p for p in p_cat_pdf if p["id"] == st.session_state.get("panneau_choisi_id")), None) if p_cat_pdf else None
    o_choisi_pdf = next((o for o in o_cat_pdf if o["id"] == st.session_state.get("onduleur_choisi_id")), None) if o_cat_pdf else None
    b_choisi_pdf = next((b for b in b_cat_pdf if b["id"] == st.session_state.get("batterie_choisie_id")), None) if b_cat_pdf and st.session_state.get("inclure_batterie") else None
    panneaux_par_pan_pdf = st.session_state.get("panneaux_par_pan", {})
    nb_tot_pv_pdf = sum(panneaux_par_pan_pdf.values()) if isinstance(panneaux_par_pan_pdf, dict) else 0
    dist_toit_pdf = float(st.session_state.get("distance_toit_onduleur", 0.0))
    section_dc_pdf = estimer_section_cable(courant_a=12.5, longueur_m=max(dist_toit_pdf, 1.0), chute_tension_max_pct=3.0, tension_v=400.0)
    metrages_pdf = estimer_metrage_cablage(nb_panneaux=nb_tot_pv_pdf, distance_toit_onduleur_m=max(dist_toit_pdf, 1.0))

    csv_r_pdf = st.session_state.get("conso_horaire_csv")
    if csv_r_pdf is not None:
        try:
            conso_m_pdf = [float(v) for v in csv_r_pdf.groupby(csv_r_pdf.index.month).sum().values]
        except Exception:
            conso_m_pdf = None
    else:
        conso_m_pdf = None

    resultats_pdf = {
        "production_pv_annuelle":  prod_pv_an,
        "production_pv_mensuelle": list(prod_pv_m),
        "conso_mensuelle":         conso_m_pdf,
        "besoin_ecs_kwh":          ecs_r_kwh,
        "besoin_chauffage_kwh":    chauf_r_kwh,
        "besoin_elec_kwh":         elec_r,
        "bilan_pv":                bilan_pv_bat,
        "bilan_th":                bilan_th,
        "vol_ballon":              vol_ballon,
        "economies_annuelles":     eco_an_r,
        "capex_total":             capex_tot_r,
        "payback_simple":          pb_r,
        "van":                     van_r,
        "pans_toiture":            st.session_state.get("pans_toiture", []),
        "equipements": {
            "panneau": p_choisi_pdf, "onduleur": o_choisi_pdf,
            "batterie": b_choisi_pdf, "nb_panneaux": nb_tot_pv_pdf
        },
        "cablage": {
            "section_dc_mm2": section_dc_pdf,
            "cable_dc_m": metrages_pdf["cable_dc_m"],
            "cable_ac_m": metrages_pdf["cable_ac_m"],
            "cable_terre_m": metrages_pdf["cable_terre_m"]
        },
        "capex_details": {
            "panneaux_fact": nb_tot_pv_pdf * (p_choisi_pdf["prix_unitaire_eur"] if p_choisi_pdf else 0.0),
            "onduleur_fact": o_choisi_pdf["prix_eur"] if o_choisi_pdf else 0.0,
            "pose_fact": float(st.session_state.get("forfait_pose_installation", 0.0)),
            "thermique_fact": capex_th_r,
            "batterie_fact": capex_bat_r
        },
        "dimensionnement": {
            "surface_m2": st.session_state.get("surface_m2", 0.0),
            "duree_financement": st.session_state.get("duree_financement", 20),
            "taux_act": st.session_state.get("taux_act", 0.03),
            "kwp_pvgis": kwp_r, "inclinaison_pv": inc_r, "azimut_pv": az_r,
            "surface_th": s_th_r, "rendement_th": rend_th, "capacite_bat": cap_bat,
            "reseau_type": reseau_r, "cos_phi": cos_r,
            "injection_limite_active": inj_act, "injection_limite_kw": inj_kw,
            "umur": umur_r, "uph": uph_r, "upb": upb_r, "dh14": dh14_r,
            "prix_reseau": pr_res, "tarif_rachat": tr_res,
        },
        "station_meteo":   station_str,
        "disclaimer_dpe":  DISCLAIMER_DPE,
    }
    client_pdf = {
        "prenom": st.session_state.get("client_prenom",""),
        "nom":    st.session_state.get("client_nom",""),
        "email":  st.session_state.get("client_email",""),
        "societe":st.session_state.get("client_societe",""),
        "adresse":st.session_state.get("adresse_formatee","—"),
        "notes":  st.session_state.get("client_notes",""),
        "installateur_nom": st.session_state.get("installateur_nom",""),
        "date":   pd.Timestamp.now().strftime("%d/%m/%Y"),
        "nom_etude": etude_active.get("nom_etude", "Installation Solaire"),
        "maison_image_path": st.session_state.get("maison_temp_path")
    }

    if st.button(":material/picture_as_pdf: Générer le rapport PDF"):
        with st.spinner("Génération du rapport…"):
            try:
                pdf_file = generer_rapport_pdf(
                    resultats=resultats_pdf, client_info=client_pdf,
                    logo_path=st.session_state.get("logo_temp_path"),
                    output_path="rapport_ecodimpro.pdf"
                )
                with open(pdf_file, "rb") as f:
                    pdf_bytes = f.read()
                st.success("Rapport PDF généré !")
                st.download_button(
                    ":material/download: Télécharger",
                    data=pdf_bytes,
                    file_name=f"Rapport_EcoDimPro_{client_n.replace(' ','_') or 'rapport'}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Erreur génération : {e}")

    st.caption(f"⚠️ {DISCLAIMER_DPE}")

    # Navigation
    st.markdown("---")
    col_prev, _ = st.columns(2)
    with col_prev:
        if st.button("← Étape 7 : Économie", use_container_width=True):
            _sauvegarder(); st.session_state["current_step"] = 7; st.rerun()

# ─── Auto-save ────────────────────────────────────────────────────────────────
_sauvegarder()
