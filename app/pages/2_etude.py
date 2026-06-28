"""
app/pages/2_etude.py — Étude Complète (6 onglets)
Localisation · Électricité · ECS & Chauffage · Solaire · Économie · Résultats
Utilise les paramètres réglementaires officiels (méthode 3CL-DPE, arrêté 31 mars 2021).
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
from ecodimpro.ui import inject_css, render_sidebar, creer_jauge
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
    # Nouveaux présets réglementaires
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

# ─── Garde : redirection si pas de dossier actif ─────────────────────────────
if not st.session_state.get("etudes"):
    st.warning(":material/warning: Aucun dossier actif. Veuillez créer ou sélectionner un dossier.")
    st.page_link("pages/1_accueil_dossiers.py", label="← Aller à la gestion des dossiers",
                  icon=":material/folder_open:")
    st.stop()

render_sidebar(st)

# ─── En-tête + bouton retour ──────────────────────────────────────────────────
col_titre, col_back = st.columns([5, 1])
with col_titre:
    etude_active = st.session_state["etudes"][st.session_state.get("active_etude_idx", 0)]
    st.markdown(
        f"<h1 class='main-title'><span style='color:#E8A33D;'>•</span> {etude_active['nom_etude']}</h1>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p class='sub-title'>Client : {etude_active['client_prenom']} {etude_active['client_nom']} · Diagnostiqueur : {st.session_state.get('installateur_nom','—')}</p>",
        unsafe_allow_html=True
    )
with col_back:
    st.write("")
    st.write("")
    if st.button(":material/arrow_back: Changer de dossier", use_container_width=True):
        _sauvegarder()
        st.switch_page("pages/1_accueil_dossiers.py")

# ─── ONGLETS ─────────────────────────────────────────────────────────────────
tab_loc, tab_toit, tab_elec, tab_ecs, tab_sol, tab_eco, tab_res = st.tabs([
    ":material/location_on: Localisation",
    ":material/roofing: Étude de Toiture",
    ":material/bolt: Électricité",
    ":material/local_fire_department: ECS & Chauffage",
    ":material/wb_sunny: Solaire",
    ":material/payments: Économie",
    ":material/insert_chart: Résultats",
])

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 1 — LOCALISATION & THERMIQUE
# ══════════════════════════════════════════════════════════════════════════════
with tab_loc:
    st.subheader(":material/person: Données Client & Installateur")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.session_state["installateur_nom"] = st.text_input(
            "Nom de l'entreprise / diagnostiqueur",
            value=st.session_state.get("installateur_nom","EcoDim Pro"))
        uploaded_logo = st.file_uploader("Logo personnalisé (PNG/JPG)", type=["png","jpg","jpeg"])
        if uploaded_logo:
            logo_data = uploaded_logo.read()
            st.session_state["logo_bytes"] = logo_data
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tfile.write(logo_data)
            tfile.close()  # Libère le verrou fichier sous Windows
            st.session_state["logo_temp_path"] = tfile.name
            _sauvegarder()  # Sauvegarde immédiate dans l'étude active
        
        # Bouton pour réinitialiser et nettoyer le logo de la session active
        if st.session_state.get("logo_bytes") is not None:
            if st.button(":material/delete: Réinitialiser le logo par défaut", use_container_width=True):
                st.session_state["logo_bytes"] = None
                st.session_state["logo_temp_path"] = None
                _sauvegarder()  # Sauvegarde immédiate dans l'étude active
                st.success("Logo personnalisé supprimé. Le logo transparent de l'application est restauré.")
                st.rerun()

        # Photo de la maison
        uploaded_maison = st.file_uploader("Photo de la maison (PNG/JPG) [Couverture]", type=["png","jpg","jpeg"])
        if uploaded_maison:
            maison_data = uploaded_maison.read()
            st.session_state["maison_bytes"] = maison_data
            tfile_m = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tfile_m.write(maison_data)
            tfile_m.close()  # Libère le verrou fichier sous Windows
            st.session_state["maison_temp_path"] = tfile_m.name
            _sauvegarder()  # Sauvegarde immédiate dans l'étude active
            
        if st.session_state.get("maison_bytes") is not None:
            st.image(st.session_state["maison_bytes"], caption="Aperçu de la photo de la maison", width=250)
            if st.button(":material/delete: Réinitialiser la photo de la maison", use_container_width=True):
                st.session_state["maison_bytes"] = None
                st.session_state["maison_temp_path"] = None
                _sauvegarder()  # Sauvegarde immédiate dans l'étude active
                st.success("Photo de la maison supprimée.")
                st.rerun()
                
        st.session_state["client_societe"] = st.text_input(
            "Société du client", value=st.session_state.get("client_societe",""))

    with col_c2:
        st.session_state["client_prenom"] = st.text_input("Prénom", value=st.session_state.get("client_prenom","Albert"))
        st.session_state["client_nom"]    = st.text_input("Nom",    value=st.session_state.get("client_nom","Mercier"))
        client_email = st.text_input("Email", value=st.session_state.get("client_email",""))
        st.session_state["client_email"] = client_email
        if client_email and not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", client_email):
            st.warning("Format d'e-mail invalide.")
        st.session_state["client_notes"] = st.text_area(
            "Notes d'audit", value=st.session_state.get("client_notes",""))

    st.markdown("---")
    st.subheader(":material/location_on: Localisation GPS")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        adresse = st.text_input("Adresse du projet", value=st.session_state.get("adresse_formatee","14 Avenue verte, Bordeaux"))
        st.session_state["adresse_formatee"] = adresse

        if st.button(":material/search: Rechercher"):
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
            lat = st.number_input("Latitude (°)",  value=float(st.session_state.get("latitude",44.8378)), format="%.4f")
            lon = st.number_input("Longitude (°)", value=float(st.session_state.get("longitude",-0.5792)), format="%.4f")
            st.session_state["latitude"]  = lat
            st.session_state["longitude"] = lon
        else:
            lat = float(st.session_state.get("latitude",  44.8378))
            lon = float(st.session_state.get("longitude", -0.5792))
            st.write(f"**Coordonnées :** {lat:.4f}°, {lon:.4f}°")

        # Zone climatique — sélecteur officiel avec DH14
        zone_auto = detecter_zone_climatique(lat, lon)
        zones_opt = list(ZONES_CLIMATIQUES.keys())
        val_zone  = st.session_state.get("zone_climatique_choisie", zone_auto)
        if val_zone not in zones_opt:
            val_zone = zone_auto
        zone_clim = st.selectbox(
            "Zone climatique (3CL-DPE)",
            zones_opt,
            index=zones_opt.index(val_zone),
            format_func=lambda z: ZONES_CLIMATIQUES[z]["label"],
            help="Pré-sélectionnée selon les coordonnées GPS. Modifiable pour les communes d'altitude."
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

    with col_m2:
        st.markdown('<div class="card-neutre"><h4>Vue Satellite du Projet</h4></div>', unsafe_allow_html=True)
        try:
            carte = folium.Map(location=[lat, lon], zoom_start=18, tiles=None)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri', name='Satellite'
            ).add_to(carte)
            folium.Marker([lat, lon], popup="Site", icon=folium.Icon(color='red')).add_to(carte)
            st_folium(carte, width=480, height=340, key="sat_map")
        except Exception as e:
            st.error(f"Carte : {e}")

    # ── Caractéristiques thermiques ──────────────────────────────────────────
    st.markdown("---")
    st.subheader(":material/home: Caractéristiques Thermiques du Logement")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        surface_m2 = st.number_input("Surface habitable (m²)", min_value=10.0, max_value=1000.0,
            value=float(st.session_state.get("surface_m2",120.0)), step=10.0)
        st.session_state["surface_m2"] = surface_m2

        # Isolation murs — UMUR_PAR_PERIODE officiel par zone
        val_umur_p = st.session_state.get("umur_periode", PERIODES_UMUR[0])
        if val_umur_p not in PERIODES_UMUR:
            val_umur_p = PERIODES_UMUR[0]
        umur_periode = st.selectbox(
            "Isolation des murs — période et type",
            PERIODES_UMUR,
            index=PERIODES_UMUR.index(val_umur_p),
            format_func=lambda k: UMUR_PAR_PERIODE[k]["label"]
        )
        st.session_state["umur_periode"] = umur_periode
        umur = UMUR_PAR_PERIODE[umur_periode][zone_clim]
        st.info(f"U mur retenu (zone {zone_clim}) : **{umur:.2f} W/m²K**")

        # Toiture
        val_toit = st.session_state.get("type_toiture", TYPES_TOITURE[0])
        if val_toit not in TYPES_TOITURE:
            val_toit = TYPES_TOITURE[0]
        type_toiture = st.selectbox("Type et isolation de la toiture", TYPES_TOITURE,
            index=TYPES_TOITURE.index(val_toit))
        st.session_state["type_toiture"] = type_toiture
        uph = UPH_TOITURE[type_toiture]
        st.info(f"U toiture retenu : **{uph:.2f} W/m²K**")

        # Plancher bas — valeur officielle par défaut
        upb = UPB_PLANCHER_BAS_DEFAUT
        st.info(f"U plancher bas (officiel) : **{upb:.2f} W/m²K**")

    with col_t2:
        # Affichage des U retenus dans une card
        gv_approx = umur*(surface_m2*0.6) + uph*(surface_m2*0.3) + upb*(surface_m2*0.1)
        st.markdown(f"""
        <div class="card-neutre">
            <div style="font-size:.75rem;color:#64748B;margin-bottom:.5rem;">Coefficients U retenus (3CL-DPE) — Zone {zone_clim}</div>
            <table style="width:100%;font-size:.82rem;border-collapse:collapse;">
                <tr><td style="color:#64748B;">Murs (60 % de la surface)</td>
                    <td style="font-weight:600;text-align:right;">{umur:.2f} W/m²K</td></tr>
                <tr><td style="color:#64748B;">Toiture (30 % de la surface)</td>
                    <td style="font-weight:600;text-align:right;">{uph:.2f} W/m²K</td></tr>
                <tr><td style="color:#64748B;">Plancher bas (10 % de la surface)</td>
                    <td style="font-weight:600;text-align:right;">{upb:.2f} W/m²K</td></tr>
                <tr style="border-top:1px solid #E2E8F0;"><td style="font-weight:700;padding-top:.3rem;">GV approx.</td>
                    <td style="font-weight:700;text-align:right;font-family:'JetBrains Mono',monospace;">{gv_approx:.1f} W/K</td></tr>
            </table>
        </div>""", unsafe_allow_html=True)

        # Stocker pour les calculs
        st.session_state["umur"]    = umur
        st.session_state["uph"]     = uph
        st.session_state["upb"]     = upb
        st.session_state["dh14"]    = dh14_zone

        st.markdown('<div class="card-neutre"><h4>Avertissement réglementaire</h4></div>', unsafe_allow_html=True)
        st.caption(
            "⚠️ **Estimation indicative** — Les calculs thermiques sont basés sur les coefficients "
            "de référence de la méthode 3CL-DPE (arrêté 31 mars 2021). Cette simulation ne constitue "
            "pas un **DPE officiel** et ne peut se substituer à un diagnostic réalisé par un "
            "diagnostiqueur certifié."
        )



# ══════════════════════════════════════════════════════════════════════════════
# ONGLET TOITURE — ÉTUDE DE TOITURE TECHNIQUE
# ══════════════════════════════════════════════════════════════════════════════
with tab_toit:
    st.subheader(":material/roofing: Étude de Toiture Technique")
    st.markdown(
        "<p style='color:#64748B; font-size:.9rem; margin-bottom:1.5rem;'>"
        "Définissez les différents pans de toiture disponibles pour l'installation photovoltaïque. "
        "Les obstacles et zones d'ombrage partiel seront déduits automatiquement pour calculer la surface utile réelle."
        "</p>",
        unsafe_allow_html=True
    )

    pans = st.session_state.get("pans_toiture")
    if not isinstance(pans, list) or len(pans) == 0:
        pans = [
            {
                "nom": "Pan principal Sud",
                "type": "Toiture en pente",
                "surface_disponible_m2": 40.0,
                "orientation": "S",
                "azimut": 0.0,
                "inclinaison": 30,
                "surface_obstacles_m2": 2.0,
                "surface_utile_m2": 38.0,
                "ombrage_partiel": False
            }
        ]
        st.session_state["pans_toiture"] = pans

    # Table de conversion des orientations textuelles vers les azimuts (S=0, E=-90, O=90, etc.)
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

    # Affichage des pans sous forme de cartes d'édition
    pans_a_supprimer = []
    
    for i, pan in enumerate(pans):
        with st.expander(f"Pan n°{i+1} : {pan.get('nom', 'Nouveau pan')} ({pan.get('surface_utile_m2', 0.0):.1f} m² utiles)", expanded=True):
            col_p1, col_p2 = st.columns(2)
            
            with col_p1:
                pan["nom"] = st.text_input("Nom du pan", value=pan.get("nom", f"Pan {i+1}"), key=f"pan_nom_{i}")
                
                type_opts = ["Toiture en pente", "Toiture terrasse"]
                t_val = pan.get("type", "Toiture en pente")
                pan["type"] = st.selectbox(
                    "Type de toiture",
                    type_opts,
                    index=type_opts.index(t_val) if t_val in type_opts else 0,
                    key=f"pan_type_{i}"
                )
                
                pan["surface_disponible_m2"] = st.number_input(
                    "Surface disponible brute (m²)",
                    min_value=1.0,
                    max_value=2000.0,
                    value=float(pan.get("surface_disponible_m2", 30.0)),
                    step=5.0,
                    key=f"pan_surf_{i}"
                )
                
                # Saisie obstacles
                st.markdown("<div style='font-size:.85rem;font-weight:600;margin-top:.8rem;'>Obstacles / Réflections</div>", unsafe_allow_html=True)
                c_chem = st.number_input("Nombre de cheminées (1m² unitaire)", min_value=0, max_value=20, value=0, key=f"pan_chem_{i}")
                c_vel = st.number_input("Nombre de fenêtres de toit/velux (2m² unitaire)", min_value=0, max_value=20, value=0, key=f"pan_velux_{i}")
                obstacles_m2 = (c_chem * 1.0) + (c_vel * 2.0)
                pan["surface_obstacles_m2"] = obstacles_m2
                
            with col_p2:
                # Orientation
                o_val = pan.get("orientation", "S")
                if o_val not in orientations_keys:
                    o_val = "S"
                ori_idx = orientations_keys.index(o_val)
                
                orientation_sel = st.selectbox(
                    "Orientation",
                    orientations_keys,
                    index=ori_idx,
                    format_func=lambda k: orientations_map[k]["label"],
                    key=f"pan_ori_{i}"
                )
                pan["orientation"] = orientation_sel
                pan["azimut"] = orientations_map[orientation_sel]["azimut"]
                
                # Inclinaison
                default_inc = 30 if pan["type"] == "Toiture en pente" else 15
                pan["inclinaison"] = st.number_input(
                    "Inclinaison du système (°)",
                    min_value=0,
                    max_value=90,
                    value=int(pan.get("inclinaison", default_inc)),
                    step=5,
                    key=f"pan_inc_{i}",
                    help="Pour toiture terrasse, indiquez l'angle des équerres de fixation (ex: 15°)."
                )
                
                pan["ombrage_partiel"] = st.checkbox(
                    "Ombrage partiel connu (arbres, voisin, etc.)",
                    value=bool(pan.get("ombrage_partiel", False)),
                    key=f"pan_ombr_{i}",
                    help="Cocher cette case applique un abattement forfaitaire de -10% sur la production estimée de ce pan."
                )
                
                # Calcul de la surface utile
                surf_utile = max(0.0, pan["surface_disponible_m2"] - obstacles_m2)
                pan["surface_utile_m2"] = surf_utile
                
                st.markdown(f"""
                <div style='background:#F1F5F9; border-radius:6px; padding:.8rem; margin-top:1.5rem; text-align:center;'>
                    <span style='font-size:.75rem; color:#64748B; text-transform:uppercase; font-weight:600;'>Surface Utile Réelle</span><br>
                    <span style='font-size:1.6rem; font-family:monospace; font-weight:700; color:#1E293B;'>{surf_utile:.1f} m²</span>
                </div>""", unsafe_allow_html=True)
                
            # Bouton de suppression du pan si plus d'un pan
            if len(pans) > 1:
                if st.button(f":material/delete: Supprimer ce pan n°{i+1}", key=f"del_pan_{i}"):
                    pans_a_supprimer.append(i)

    # Action effective de suppression
    if pans_a_supprimer:
        for idx in sorted(pans_a_supprimer, reverse=True):
            pans.pop(idx)
        st.session_state["pans_toiture"] = pans
        st.success("Pan de toiture supprimé.")
        st.rerun()

    # Bouton d'ajout de pan
    if st.button(":material/add: Ajouter un pan de toiture", use_container_width=True):
        pans.append({
            "nom": f"Pan n°{len(pans)+1}",
            "type": "Toiture en pente",
            "surface_disponible_m2": 30.0,
            "orientation": "S",
            "azimut": 0.0,
            "inclinaison": 30,
            "surface_obstacles_m2": 0.0,
            "surface_utile_m2": 30.0,
            "ombrage_partiel": False
        })
        st.session_state["pans_toiture"] = pans
        st.rerun()

    st.session_state["pans_toiture"] = pans

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 2 — BESOINS ÉLECTRIQUES
# ══════════════════════════════════════════════════════════════════════════════
with tab_elec:
    st.subheader(":material/bolt: Besoins Électriques Spécifiques")
    st.caption("Consommation électrique annuelle hors ECS et chauffage.")

    mode_elec_opt = ["Liste des appareils", "Import de fichier CSV de consommation"]
    val_mode = st.session_state.get("mode_elec","Liste des appareils")
    mode_elec = st.radio("Mode d'évaluation", mode_elec_opt,
        index=mode_elec_opt.index(val_mode) if val_mode in mode_elec_opt else 0)
    st.session_state["mode_elec"] = mode_elec

    conso_horaire_csv = st.session_state.get("conso_horaire_csv")
    elec_annuel_kwh   = float(st.session_state.get("elec_annuel_kwh", 0.0))

    if mode_elec == "Liste des appareils":
        appareils_data = st.session_state.get("appareils_list") or [
            {"nom":"Réfrigérateur-Congélateur","puissance_w":250.0,"heures_jour":24.0,"jours_semaine":7.0},
            {"nom":"Lave-vaisselle","puissance_w":1800.0,"heures_jour":1.2,"jours_semaine":5.0},
            {"nom":"Lave-linge","puissance_w":2000.0,"heures_jour":1.0,"jours_semaine":4.0},
            {"nom":"Four électrique","puissance_w":2500.0,"heures_jour":0.5,"jours_semaine":7.0},
            {"nom":"Téléviseur principal","puissance_w":100.0,"heures_jour":4.0,"jours_semaine":7.0},
            {"nom":"Ordinateur portable","puissance_w":60.0,"heures_jour":8.0,"jours_semaine":5.0},
            {"nom":"Éclairage LED & Veilles","puissance_w":150.0,"heures_jour":6.0,"jours_semaine":7.0},
        ]
        st.session_state["appareils_list"] = appareils_data

        edited_df = st.data_editor(
            pd.DataFrame(appareils_data), num_rows="dynamic",
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
        elec_annuel_kwh = calc_besoin_elec(appareils_clean)
        st.session_state["elec_annuel_kwh"]   = elec_annuel_kwh
        st.session_state["conso_horaire_csv"] = None
        conso_horaire_csv = None

        st.markdown(f"""
        <div class="card-pv">
            <div style="font-size:.9rem;color:#9CA3AF;">Consommation annuelle estimée</div>
            <div style="font-size:1.8rem;font-family:'JetBrains Mono',monospace;font-weight:600;color:#E8A33D;">
                {elec_annuel_kwh:,.1f} <span style="font-size:1.1rem;">kWh/an</span>
            </div>
        </div>""", unsafe_allow_html=True)

    else:
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


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 3 — ECS & CHAUFFAGE
# ══════════════════════════════════════════════════════════════════════════════
with tab_ecs:
    st.subheader(":material/local_fire_department: ECS & Chauffage")

    col_e1, col_e2 = st.columns(2)

    # ── ECS ──────────────────────────────────────────────────────────────────
    with col_e1:
        st.markdown('<div class="card-thermique"><h4>Eau Chaude Sanitaire (ECS)</h4></div>', unsafe_allow_html=True)

        nb_personnes = st.number_input("Nombre d'occupants", min_value=0, max_value=20,
            value=int(st.session_state.get("nb_personnes",4)), step=1)
        st.session_state["nb_personnes"] = nb_personnes

        # Scénario ECS — préset réglementaire ou saisie manuelle
        scenarios_opt = list(SCENARIOS_ECS.keys())
        val_sc = st.session_state.get("scenario_ecs", scenarios_opt[0])
        if val_sc not in scenarios_opt:
            val_sc = scenarios_opt[0]
        scenario_ecs = st.selectbox(
            "Scénario d'usage ECS",
            scenarios_opt,
            index=scenarios_opt.index(val_sc),
            help="Valeur réglementaire DPE : 56 L/j/pers à 40°C (arrêté 31 mars 2021)."
        )
        st.session_state["scenario_ecs"] = scenario_ecs

        litres_val = SCENARIOS_ECS[scenario_ecs]
        if litres_val is None:
            litres_par_pers = st.number_input("Litres/jour/personne", min_value=10.0, max_value=200.0,
                value=float(st.session_state.get("litres_par_pers",56.0)), step=5.0)
            t_eau_froide = st.number_input("T° eau froide (°C)", min_value=2.0, max_value=25.0,
                value=float(st.session_state.get("t_eau_froide",12.0)), step=1.0)
            t_eau_chaude = st.number_input("T° eau chaude cible (°C)", min_value=40.0, max_value=85.0,
                value=float(st.session_state.get("t_eau_chaude",55.0)), step=1.0)
        else:
            litres_par_pers = litres_val
            t_eau_froide    = ECS_TEMP_FROIDE_REFERENCE    # 12°C
            t_eau_chaude    = ECS_TEMP_CHAUDE_CONVENTIONNEL # 40°C
            st.info(f"**{scenario_ecs}** : {int(litres_par_pers)} L/j/pers à {int(t_eau_chaude)}°C (eau froide : {int(t_eau_froide)}°C)")

        st.session_state["litres_par_pers"] = litres_par_pers
        st.session_state["t_eau_froide"]    = t_eau_froide
        st.session_state["t_eau_chaude"]    = t_eau_chaude

        ecs_annuel_kwh = calc_besoin_ecs(nb_personnes, litres_par_pers, t_eau_froide, t_eau_chaude)
        st.session_state["ecs_annuel_kwh"] = ecs_annuel_kwh
        st.markdown(f"""
        <div class="card-thermique">
            <div style="font-size:.9rem;color:#9CA3AF;">Besoin thermique ECS annuel</div>
            <div style="font-size:1.8rem;font-family:'JetBrains Mono',monospace;font-weight:600;color:#3DBFAE;">
                {ecs_annuel_kwh:,.1f} <span style="font-size:1.1rem;">kWh/an</span>
            </div>
        </div>""", unsafe_allow_html=True)

    # ── Chauffage ─────────────────────────────────────────────────────────────
    with col_e2:
        st.markdown('<div class="card-thermique"><h4>Chauffage Principal</h4></div>', unsafe_allow_html=True)

        inclure_chauffage = st.toggle("Activer le calcul du chauffage",
            value=st.session_state.get("inclure_chauffage",True))
        st.session_state["inclure_chauffage"] = inclure_chauffage

        # Récupérer les U et DH14 calculés dans l'onglet Localisation
        surface_m2 = float(st.session_state.get("surface_m2", 120.0))
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
            <span style="font-size:.8rem;color:#64748B;">DH14 : </span><strong style="font-family:'JetBrains Mono',monospace;">{dh14_val:,.0f} °C·h</strong><br>
            <span style="font-size:.8rem;color:#64748B;">U mur/toit/plancher : </span>
            <strong style="font-family:'JetBrains Mono',monospace;">{umur_val:.2f} / {uph_val:.2f} / {upb_val:.2f} W/m²K</strong>
            <div style="margin-top:.4rem;font-size:.72rem;color:#9CA3AF;">
                Ces valeurs proviennent de la page <em>Localisation</em>. Complétez-la d'abord si les champs affichent des valeurs par défaut.
            </div>
        </div>""", unsafe_allow_html=True)

        if inclure_chauffage:
            chauffage_kwh = calc_besoin_chauffage(
                surface_m2=surface_m2,
                umur=umur_val, uph=uph_val, upb=upb_val,
                dh14=dh14_val
            )
            st.session_state["chauffage_annuel_kwh"] = chauffage_kwh
            st.markdown(f"""
            <div class="card-thermique">
                <div style="font-size:.9rem;color:#9CA3AF;">Besoin thermique chauffage annuel</div>
                <div style="font-size:1.8rem;font-family:'JetBrains Mono',monospace;font-weight:600;color:#3DBFAE;">
                    {chauffage_kwh:,.1f} <span style="font-size:1.1rem;">kWh/an</span>
                </div>
            </div>""", unsafe_allow_html=True)
            st.caption("⚠️ Estimation 3CL-DPE simplifiée — ne se substitue pas à un DPE officiel.")
        else:
            st.session_state["chauffage_annuel_kwh"] = 0.0
            st.write("Chauffage exclu de l'étude.")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 4 — SOLAIRE & BATTERIE
# ══════════════════════════════════════════════════════════════════════════════
with tab_sol:
    st.subheader(":material/wb_sunny: Équipements Solaire & Batterie")
    st.markdown(
        "<p style='color:#64748B; font-size:.9rem; margin-bottom:1.5rem;'>"
        "Sélectionnez le matériel photovoltaïque et thermique dans le catalogue. L'application calculera automatiquement "
        "le nombre maximum de panneaux installables et estimera la section de câble conforme à la norme NF C 15-100."
        "</p>",
        unsafe_allow_html=True
    )

    # 1. Chargement des catalogues JSON
    panneaux_cat = charger_catalogue("panneaux")
    onduleurs_cat = charger_catalogue("onduleurs")
    batteries_cat = charger_catalogue("batteries")

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        st.markdown('<div class="card-pv"><h4>1. Choix du Panneau Photovoltaïque</h4></div>', unsafe_allow_html=True)
        
        if not panneaux_cat:
            st.error("Catalogue panneaux.json introuvable ou vide.")
            panneau_choisi = None
        else:
            pan_opts_ids = [p["id"] for p in panneaux_cat]
            pan_labels = [f"{p['nom']} — {p['puissance_wc']}Wc ({p['prix_unitaire_eur']:.0f}€)" for p in panneaux_cat]
            
            p_sel_id = st.session_state.get("panneau_choisi_id", pan_opts_ids[0])
            if p_sel_id not in pan_opts_ids:
                p_sel_id = pan_opts_ids[0]
            
            panneau_sel_idx = pan_opts_ids.index(p_sel_id)
            panneau_choisi_id = st.selectbox(
                "Modèle de panneau",
                options=pan_opts_ids,
                index=panneau_sel_idx,
                format_func=lambda x: pan_labels[pan_opts_ids.index(x)],
                key="sel_panneau"
            )
            st.session_state["panneau_choisi_id"] = panneau_choisi_id
            panneau_choisi = panneaux_cat[pan_opts_ids.index(panneau_choisi_id)]
            st.caption(f"Dimensions : {panneau_choisi['longueur_m']}m × {panneau_choisi['largeur_m']}m | Rendement : {panneau_choisi['rendement_pct']}%")

        # 2. Configuration des panneaux par pan de toiture
        st.markdown("<div style='font-weight:600;margin-top:1rem;margin-bottom:.5rem;'>Disposition des panneaux par pan de toiture</div>", unsafe_allow_html=True)
        
        pans = st.session_state.get("pans_toiture", [])
        panneaux_par_pan = st.session_state.get("panneaux_par_pan", {})
        
        # S'assurer que panneaux_par_pan est un dict
        if not isinstance(panneaux_par_pan, dict):
            panneaux_par_pan = {}

        total_panneaux_retenus = 0
        
        if not pans:
            st.warning("Veuillez d'abord définir au moins un pan de toiture dans l'onglet 'Étude de Toiture'.")
        elif panneau_choisi:
            for idx_pan, pan in enumerate(pans):
                nb_max = calculer_nb_panneaux_max(pan["surface_utile_m2"], panneau_choisi)
                
                # Valeur par défaut ou précédente
                key_str = str(idx_pan)
                val_prec = panneaux_par_pan.get(key_str, nb_max)
                if not isinstance(val_prec, int) or val_prec > nb_max:
                    val_prec = nb_max
                    
                nb_retenus = st.slider(
                    f"Pan n°{idx_pan+1} ({pan['nom']}) — Max {nb_max} panneaux",
                    min_value=0,
                    max_value=nb_max,
                    value=val_prec,
                    key=f"slider_pan_{idx_pan}"
                )
                panneaux_par_pan[key_str] = nb_retenus
                total_panneaux_retenus += nb_retenus
                
                p_pan_kwc = puissance_totale_kwc(nb_retenus, panneau_choisi)
                st.caption(f"Puissance sur ce pan : **{p_pan_kwc:.2f} kWc** ({nb_retenus} panneaux / {nb_retenus*panneau_choisi['surface_m2']:.1f} m² utiles occupés)")

            st.session_state["panneaux_par_pan"] = panneaux_par_pan
            
            # Puissance totale crête installée
            kwp_tot_pv = puissance_totale_kwc(total_panneaux_retenus, panneau_choisi)
            st.session_state["kwp_pvgis"] = kwp_tot_pv
            
            st.success(f"Installation totale : **{total_panneaux_retenus} panneaux** retenus — **{kwp_tot_pv:.2f} kWc** crête.")

        # 3. Choix de l'Onduleur
        st.markdown('<div class="card-pv"><h4>2. Choix de l\'Onduleur</h4></div>', unsafe_allow_html=True)
        
        if not onduleurs_cat:
            st.error("Catalogue onduleurs.json introuvable.")
            onduleur_choisi = None
        elif panneau_choisi:
            kwp_tot_pv = st.session_state.get("kwp_pvgis", 3.0)
            
            # Filtre des onduleurs compatibles (puissance à +/- 25% du kWc total)
            ond_compatibles = []
            for ond in onduleurs_cat:
                if ond["type"] == "micro":
                    # Les micro-onduleurs s'installent unitairement par panneau, donc ils sont toujours compatibles
                    ond_compatibles.append(ond)
                else:
                    # Puissance nominale de l'onduleur entre 70% et 130% de la puissance crête
                    if 0.70 * kwp_tot_pv <= ond["puissance_kw"] <= 1.30 * kwp_tot_pv:
                        ond_compatibles.append(ond)
            
            if not ond_compatibles:
                # Fallback sur tout le catalogue si aucun compatible
                ond_compatibles = onduleurs_cat
                
            ond_ids = [o["id"] for o in ond_compatibles]
            ond_labels = [f"{o['nom']} ({o['puissance_kw']} kW, {o['prix_eur']:.0f}€)" for o in ond_compatibles]
            
            ond_sel_id = st.session_state.get("onduleur_choisi_id", ond_ids[0])
            if ond_sel_id not in ond_ids:
                ond_sel_id = ond_ids[0]
                
            onduleur_choisi_id = st.selectbox(
                "Onduleur compatible (±25%)",
                options=ond_ids,
                index=ond_ids.index(ond_sel_id),
                format_func=lambda x: ond_labels[ond_ids.index(x)],
                key="sel_onduleur"
            )
            st.session_state["onduleur_choisi_id"] = onduleur_choisi_id
            onduleur_choisi = onduleurs_cat[[o["id"] for o in onduleurs_cat].index(onduleur_choisi_id)]

    with col_s2:
        # Solaire Thermique (inchangé)
        st.markdown('<div class="card-thermique"><h4>Solaire Thermique (ECS)</h4></div>', unsafe_allow_html=True)
        surface_th   = st.number_input("Surface capteurs (m²)", min_value=0.0, max_value=50.0, value=float(st.session_state.get("surface_th",4.0)), step=0.5)
        rendement_th = st.number_input("Rendement optique moyen", min_value=0.10, max_value=0.90, value=float(st.session_state.get("rendement_th",0.50)), step=0.05)
        st.session_state.update(surface_th=surface_th, rendement_th=rendement_th)

        # 4. Batterie de Stockage
        st.markdown("---")
        st.markdown('<div class="card-pv"><h4>3. Batterie de Stockage</h4></div>', unsafe_allow_html=True)
        inclure_bat = st.toggle("Activer la batterie", value=st.session_state.get("inclure_batterie",False))
        st.session_state["inclure_batterie"] = inclure_bat
        
        if inclure_bat and batteries_cat:
            bat_opts_ids = [b["id"] for b in batteries_cat]
            bat_labels = [f"{b['nom']} — {b['capacite_kwh']} kWh ({b['prix_eur']:.0f}€)" for b in batteries_cat]
            
            b_sel_id = st.session_state.get("batterie_choisie_id", bat_opts_ids[0])
            if b_sel_id not in bat_opts_ids:
                b_sel_id = bat_opts_ids[0]
                
            batterie_choisie_id = st.selectbox(
                "Modèle de batterie",
                options=bat_opts_ids,
                index=bat_opts_ids.index(b_sel_id),
                format_func=lambda x: bat_labels[bat_opts_ids.index(x)],
                key="sel_batterie"
            )
            st.session_state["batterie_choisie_id"] = batterie_choisie_id
            batterie_choisie = batteries_cat[bat_opts_ids.index(batterie_choisie_id)]
            st.session_state["capacite_bat"] = float(batterie_choisie["capacite_kwh"])
            st.session_state["rendement_bat"] = float(batterie_choisie["rendement_pct"] / 100.0)
            
            st.caption(f"Technologie : {batterie_choisie['technologie']} | Cycles garantis : {batterie_choisie['cycles_garantis']}")
        else:
            st.session_state["capacite_bat"] = 0.0
            st.session_state["rendement_bat"] = 0.90
            batterie_choisie = None

        # 5. Section et métrage de câblage (NF C 15-100)
        st.markdown("---")
        st.markdown('<div class="card-neutre"><h4>4. Dimensionnement Câblage & Conformité</h4></div>', unsafe_allow_html=True)
        
        dist_toit = st.number_input(
            "Longueur chemin de câble toit-onduleur (m)",
            min_value=2.0,
            max_value=150.0,
            value=float(st.session_state.get("distance_toit_onduleur", 15.0)),
            step=5.0,
            key="dist_toit_ond"
        )
        st.session_state["distance_toit_onduleur"] = dist_toit
        
        # Courant nominal DC moyen par chaîne = ~12.5 A max
        courant_dc = 12.5
        section_dc = estimer_section_cable(courant_a=courant_dc, longueur_m=dist_toit, chute_tension_max_pct=3.0, tension_v=400.0)
        metrages = estimer_metrage_cablage(nb_panneaux=total_panneaux_retenus, distance_toit_onduleur_m=dist_toit)
        
        st.markdown(f"""
        <div style="background:#FFF; padding:.8rem; border:1px solid #E2E8F0; border-radius:6px; font-size:.82rem;">
            <table style="width:100%;">
                <tr><td style="color:#64748B;">Section câble DC recommandée</td>
                    <td style="text-align:right; font-weight:600; font-family:monospace; color:#E8A33D;">{section_dc} mm²</td></tr>
                <tr><td style="color:#64748B;">Longueur câble DC estimée</td>
                    <td style="text-align:right; font-weight:600; font-family:monospace;">{metrages['cable_dc_m']} m</td></tr>
                <tr><td style="color:#64748B;">Longueur câble AC estimée</td>
                    <td style="text-align:right; font-weight:600; font-family:monospace;">{metrages['cable_ac_m']} m</td></tr>
                <tr><td style="color:#64748B;">Longueur câble Terre estimée</td>
                    <td style="text-align:right; font-weight:600; font-family:monospace;">{metrages['cable_terre_m']} m</td></tr>
            </table>
            <div style="font-size:.7rem; color:#94A3B8; margin-top:.4rem; line-height:1.2;">
                *Calculs indicatifs selon NF C 15-100 (chute de tension max 3%). À valider sur chantier par l'installateur.
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="card-pv"><h4>Paramètres de Raccordement Réseau</h4></div>', unsafe_allow_html=True)
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        net_opts = ["230V monophasé","400V triphasé (230V L-N / 400V L-L)"]
        val_net  = st.session_state.get("reseau_type","230V monophasé")
        reseau_type = st.selectbox("Type raccordement", net_opts, index=net_opts.index(val_net) if val_net in net_opts else 0)
        cos_phi = st.number_input("Facteur de puissance (cos φ)", min_value=0.80, max_value=1.00, value=float(st.session_state.get("cos_phi",0.95)), step=0.01)
        st.session_state.update(reseau_type=reseau_type, cos_phi=cos_phi)
    with col_n2:
        inj_active = st.toggle("Limite d'injection réseau", value=st.session_state.get("injection_limite_active",False))
        st.session_state["injection_limite_active"] = inj_active
        inj_kw = st.number_input("Puissance max injectée (kW)", min_value=0.0, max_value=250.0,
            value=float(st.session_state.get("injection_limite_kw",3.0) or 3.0), step=0.5) if inj_active else None
        st.session_state["injection_limite_kw"] = inj_kw


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 5 — ÉCONOMIE
# ══════════════════════════════════════════════════════════════════════════════
with tab_eco:
    st.subheader(":material/payments: Hypothèses Économiques — CAPEX & Tarifs")

    col_eco1, col_eco2 = st.columns(2)
    with col_eco1:
        st.markdown('<div class="card-neutre"><h4>Tarifs Énergie & Durée</h4></div>', unsafe_allow_html=True)
        prix_reseau  = st.number_input("Prix achat réseau (€/kWh)", min_value=0.01, max_value=1.0, value=float(st.session_state.get("prix_reseau",0.2516)), step=0.01)
        tarif_rachat = st.number_input("Tarif rachat surplus (€/kWh)", min_value=0.00, max_value=0.5, value=float(st.session_state.get("tarif_rachat",0.13)), step=0.01)
        duree_fin    = st.number_input("Durée exploitation (ans)", min_value=5, max_value=40, value=int(st.session_state.get("duree_financement",20)), step=5)
        taux_act_pct = float(st.session_state.get("taux_act",0.03)) * 100
        taux_act     = st.number_input("Taux actualisation (%)", min_value=0.0, max_value=10.0, value=taux_act_pct, step=0.5) / 100
        st.session_state.update(prix_reseau=prix_reseau, tarif_rachat=tarif_rachat, duree_financement=duree_fin, taux_act=taux_act)

    with col_eco2:
        st.markdown('<div class="card-neutre"><h4>CAPEX Détaillé (Matériel & Pose)</h4></div>', unsafe_allow_html=True)
        
        # Récupération des prix du catalogue
        p_cat = charger_catalogue("panneaux")
        o_cat = charger_catalogue("onduleurs")
        b_cat = charger_catalogue("batteries")
        
        p_choisi = next((p for p in p_cat if p["id"] == st.session_state.get("panneau_choisi_id")), None) if p_cat else None
        o_choisi = next((o for o in o_cat if o["id"] == st.session_state.get("onduleur_choisi_id")), None) if o_cat else None
        
        inclure_bat = st.session_state.get("inclure_batterie", False)
        b_choisi = next((b for b in b_cat if b["id"] == st.session_state.get("batterie_choisie_id")), None) if b_cat and inclure_bat else None
        
        panneaux_par_pan = st.session_state.get("panneaux_par_pan", {})
        nb_tot_pv = sum(panneaux_par_pan.values()) if isinstance(panneaux_par_pan, dict) else 0
        
        # Saisie d'un forfait d'installation (pose + structure fixation + coffret AC/DC)
        forfait_pose = st.number_input(
            "Forfait Pose, Fixations & Main d'œuvre (€)",
            min_value=500.0,
            max_value=25000.0,
            value=float(st.session_state.get("forfait_pose_installation", 2500.0)),
            step=100.0,
            key="forfait_pose_install"
        )
        st.session_state["forfait_pose_installation"] = forfait_pose
        
        # Solaire Thermique coût unitaire au m²
        prix_th_m2 = st.number_input(
            "Coût Solaire Thermique (€/m²)",
            min_value=100.0,
            max_value=5000.0,
            value=float(st.session_state.get("prix_th_m2", 700.0)),
            step=50.0
        )
        st.session_state["prix_th_m2"] = prix_th_m2
        
        # Calculs budgétaires
        cost_panels = nb_tot_pv * (p_choisi["prix_unitaire_eur"] if p_choisi else 0.0)
        cost_inverter = o_choisi["prix_eur"] if o_choisi else 0.0
        cost_battery = b_choisi["prix_eur"] if b_choisi else 0.0
        
        capex_pv_calc = cost_panels + cost_inverter + forfait_pose
        surf_th = float(st.session_state.get("surface_th", 4.0))
        capex_th_calc = surf_th * prix_th_m2
        capex_bat_calc = cost_battery
        capex_tot = capex_pv_calc + capex_th_calc + capex_bat_calc
        
        # Enregistrement pour l'export et les pages suivantes
        st.session_state["prix_pv_kwp"] = capex_pv_calc / max(0.1, st.session_state.get("kwp_pvgis", 3.0)) # pour rétrocompatibilité
        st.session_state["prix_bat_kwh"] = capex_bat_calc / max(1.0, st.session_state.get("capacite_bat", 1.0)) if inclure_bat else 0.0
        
        st.session_state["capex_pv_calc"] = capex_pv_calc
        st.session_state["capex_th_calc"] = capex_th_calc
        st.session_state["capex_bat_calc"] = capex_bat_calc
        st.session_state["capex_total"] = capex_tot
        
        st.markdown(f"""
        <div class="card-neutre">
            <div style="font-size:.75rem;color:#64748B;margin-bottom:.4rem;">CAPEX Détaillé Estimé</div>
            <table style="width:100%;font-size:.82rem;border-collapse:collapse;">
                <tr><td style="color:#64748B;">Panneaux PV ({nb_tot_pv} u.)</td><td style="text-align:right;font-weight:600;">{cost_panels:,.0f} €</td></tr>
                <tr><td style="color:#64748B;">Onduleur ({o_choisi['nom'] if o_choisi else 'aucun'})</td><td style="text-align:right;font-weight:600;">{cost_inverter:,.0f} €</td></tr>
                <tr><td style="color:#64748B;">Pose, fixations & câblage</td><td style="text-align:right;font-weight:600;">{forfait_pose:,.0f} €</td></tr>
                <tr style="border-bottom:1px solid #E2E8F0;padding-bottom:.2rem;"><td style="color:#1E3A8A;font-weight:500;">Sous-total PV</td><td style="text-align:right;font-weight:600;color:#1E3A8A;">{capex_pv_calc:,.0f} €</td></tr>
                <tr><td style="color:#64748B;padding-top:.3rem;">Solaire Thermique ({surf_th:.1f} m²)</td><td style="text-align:right;font-weight:600;padding-top:.3rem;">{capex_th_calc:,.0f} €</td></tr>
                <tr><td style="color:#64748B;">Batterie ({b_choisi['nom'] if b_choisi else 'aucune'})</td><td style="text-align:right;font-weight:600;">{capex_bat_calc:,.0f} €</td></tr>
                <tr style="border-top:1px solid #E2E8F0;"><td style="font-weight:700;padding-top:.3rem;font-size:.9rem;">Total CAPEX</td>
                    <td style="font-weight:700;text-align:right;font-family:'JetBrains Mono',monospace;color:#E8A33D;font-size:1.15rem;">{capex_tot:,.0f} €</td></tr>
            </table>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 6 — RÉSULTATS & RAPPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_res:
    st.subheader(":material/insert_chart: Synthèse de Simulation & Rapport")

    # Relecture des variables de session
    lat_r    = float(st.session_state.get("latitude", 44.8378))
    lon_r    = float(st.session_state.get("longitude", -0.5792))
    kwp_r    = float(st.session_state.get("kwp_pvgis", 3.0))
    inc_r    = int(st.session_state.get("inclinaison_pv", 30))
    az_r     = int(st.session_state.get("azimut_pv", 0))
    pr_r     = float(st.session_state.get("pr_pv", 0.85))
    s_th_r   = float(st.session_state.get("surface_th", 4.0))
    rend_th  = float(st.session_state.get("rendement_th", 0.50))
    inc_bat  = st.session_state.get("inclure_batterie", False)
    cap_bat  = float(st.session_state.get("capacite_bat", 0.0))
    rend_bat = float(st.session_state.get("rendement_bat", 0.90))
    nb_pers  = int(st.session_state.get("nb_personnes", 4))
    litres_r = float(st.session_state.get("litres_par_pers", 56.0))
    tf_r     = float(st.session_state.get("t_eau_froide", 12.0))
    tc_r     = float(st.session_state.get("t_eau_chaude", 40.0))
    elec_r   = float(st.session_state.get("elec_annuel_kwh", 3500.0))
    csv_r    = st.session_state.get("conso_horaire_csv")
    surf_r   = float(st.session_state.get("surface_m2", 120.0))
    umur_r   = float(st.session_state.get("umur",  2.50))
    uph_r    = float(st.session_state.get("uph",   0.43))
    upb_r    = float(st.session_state.get("upb",   UPB_PLANCHER_BAS_DEFAUT))
    dh14_r   = float(st.session_state.get("dh14",  33_300.0))
    inc_ch   = st.session_state.get("inclure_chauffage", True)
    pr_res   = float(st.session_state.get("prix_reseau", 0.2516))
    tr_res   = float(st.session_state.get("tarif_rachat", 0.13))
    dur_res  = int(st.session_state.get("duree_financement", 20))
    taux_r   = float(st.session_state.get("taux_act", 0.03))
    ppv_r    = float(st.session_state.get("prix_pv_kwp", 1900.0))
    pth_r    = float(st.session_state.get("prix_th_m2", 700.0))
    pbat_r   = float(st.session_state.get("prix_bat_kwh", 600.0))
    reseau_r = st.session_state.get("reseau_type","230V monophasé")
    cos_r    = float(st.session_state.get("cos_phi", 0.95))
    inj_act  = st.session_state.get("injection_limite_active", False)
    inj_kw   = st.session_state.get("injection_limite_kw")
    client_n = f"{st.session_state.get('client_prenom','')} {st.session_state.get('client_nom','')}".strip()

    with st.spinner("Calculs & simulation multi-orientations en cours…"):
        # Détection du panneau choisi pour calculer la puissance crête unitaire
        p_cat_res = charger_catalogue("panneaux")
        p_choisi_res = next((p for p in p_cat_res if p["id"] == st.session_state.get("panneau_choisi_id")), None) if p_cat_res else None
        p_wc_res = p_choisi_res["puissance_wc"] if p_choisi_res else 425.0

        pans_res = st.session_state.get("pans_toiture", [])
        panneaux_par_pan_res = st.session_state.get("panneaux_par_pan", {})
        
        prod_pv_m = pd.Series(0.0, index=range(1, 13))
        has_panels = False
        
        # Trouver le pan principal (celui avec le plus de panneaux) pour l'irradiation thermique de référence
        max_pan_idx = 0
        max_pan_count = -1
        
        for i, pan in enumerate(pans_res):
            nb_p_pan = panneaux_par_pan_res.get(str(i), 0) if isinstance(panneaux_par_pan_res, dict) else 0
            if nb_p_pan > max_pan_count:
                max_pan_count = nb_p_pan
                max_pan_idx = i
                
            if nb_p_pan > 0:
                has_panels = True
                kwp_pan = nb_p_pan * p_wc_res / 1000.0
                prod_m = production_pv_mensuelle(lat_r, lon_r, kwp_pan, pan["inclinaison"], pan["azimut"], pr_r)
                if pan.get("ombrage_partiel"):
                    prod_m = prod_m * 0.9
                prod_pv_m = prod_pv_m + prod_m

        # Fallback si aucun panneau n'a été placé sur les toits (ou catalogue introuvable)
        if not has_panels:
            prod_pv_m = production_pv_mensuelle(lat_r, lon_r, kwp_r, inc_r, az_r, pr_r)
            
        prod_pv_an = float(prod_pv_m.sum())

        # Calcul de l'irradiation annuelle sur le pan principal (thermique)
        if pans_res:
            pan_princ = pans_res[max_pan_idx]
            pvgis_data = recuperer_irradiation_pvgis(lat_r, lon_r, pan_princ["inclinaison"], pan_princ["azimut"])
        else:
            pvgis_data = recuperer_irradiation_pvgis(lat_r, lon_r, inc_r, az_r)
            
        irrad_an   = sum(m["H(i)_d"] * DAYS_IN_MONTH[m["month"]] for m in pvgis_data["outputs"]["monthly"])
        station_str= pvgis_data.get("inputs",{}).get("meteo_data",{}).get("radiation_db","PVGIS-SARAH2")
        st.session_state["station_meteo"] = station_str

        ecs_r_kwh   = calc_besoin_ecs(nb_pers, litres_r, tf_r, tc_r)
        chauf_r_kwh = calc_besoin_chauffage(surf_r, umur_r, uph_r, upb_r, dh14_r) if inc_ch else 0.0

        vol_ballon = dimensionner_ballon(nb_pers * litres_r)
        bilan_th   = couverture_ecs(s_th_r, rend_th, ecs_r_kwh, irrad_an)

        if csv_r is not None:
            # Profil horaire disponible : calcul exact par minute/heure
            bilan_pv = calc_autoconsommation(prod_pv_m, csv_r)
        else:
            # Pas de CSV : on utilise les 12 mois de production vs consommation mensuelle uniforme
            # pour capturer l'autoconsommation diurne (meilleure approximation que le ratio 35% flat)
            elec_mensuelle = pd.Series(
                [elec_r / 12.0] * 12, index=range(1, 13)
            )
            bilan_pv = calc_autoconsommation(prod_pv_m, elec_mensuelle)

        if inc_bat and cap_bat > 0:
            if csv_r is not None:
                heures  = csv_r.index.hour
                soleil  = np.where((heures >= 7) & (heures <= 19), np.sin((heures-7)/12*np.pi), 0.0)
                s_sum   = soleil.sum()
                prod_h  = pd.Series(prod_pv_an*(soleil/s_sum) if s_sum>0 else soleil, index=csv_r.index)
                gain_b  = gain_autoconsommation_avec_batterie(prod_h, csv_r, cap_bat, rend_bat)
            else:
                gain_b  = gain_autoconsommation_avec_batterie(prod_pv_m, elec_r, cap_bat, rend_bat)
            
            auto_sans = float(bilan_pv.get("energie_autoconsommee_kwh", 0.0))
            gain_kwh = float(gain_b.get("gain_kwh", 0.0))
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

        # Calcul des fallbacks traditionnels si pas en session
        capex_pv_fallback = calc_capex_pv(kwp_r, ppv_r)
        capex_th_fallback = calc_capex_thermique(s_th_r, pth_r)
        capex_bat_fallback = cap_bat * pbat_r if inc_bat else 0.0
        capex_tot_fallback = capex_pv_fallback + capex_th_fallback + capex_bat_fallback

        # Utilisation des CAPEX détaillés du catalogue
        capex_pv_r  = float(st.session_state.get("capex_pv_calc", capex_pv_fallback))
        capex_th_r  = float(st.session_state.get("capex_th_calc", capex_th_fallback))
        capex_bat_r = float(st.session_state.get("capex_bat_calc", capex_bat_fallback))
        capex_tot_r = float(st.session_state.get("capex_total", capex_tot_fallback))

        # Calcul des économies élec
        auto_kwh = prod_pv_an * (bilan_pv_bat.get("taux_autoconsommation", 50.0) / 100.0)
        surplus_kwh = max(0.0, prod_pv_an - auto_kwh)
        economies_elec = economies_annuelles(auto_kwh, pr_res, surplus_kwh, tr_res)

        # Calcul des économies thermiques (appoint évité)
        taux_couv = bilan_th.get("taux_couverture", 0.0) if isinstance(bilan_th, dict) else float(bilan_th)
        economies_th = (ecs_r_kwh * taux_couv) * pr_res

        eco_an_r = economies_elec + economies_th
        pb_r      = payback_simple(capex_tot_r, eco_an_r) if eco_an_r > 0 else None
        van_r     = van(capex_tot_r, eco_an_r, duree_ans=dur_res, taux_actualisation=taux_r)
        courant_a = (kwp_r*1000) / (230 if "monophasé" in reseau_r else 400) / cos_r

    # ── KPI ──────────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(":material/wb_sunny: Production PV",     f"{prod_pv_an:,.0f} kWh/an")
    k2.metric(":material/bolt: Conso électrique",       f"{elec_r:,.0f} kWh/an")
    k3.metric(":material/local_fire_department: ECS",  f"{ecs_r_kwh:,.0f} kWh/an")
    k4.metric(":material/payments: Économies",          f"{eco_an_r:,.0f} €/an")
    k5.metric(":material/schedule: Retour invest.",     f"{pb_r:.1f} ans" if pb_r else "—")

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
    bf4.metric("TRI approx.",    f"{((eco_an_r/capex_tot_r)*100):.1f} %/an" if capex_tot_r>0 else "—")

    # ── Production mensuelle ──────────────────────────────────────────────────
    st.markdown("---")
    mois = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]
    fig_b = go.Figure()
    fig_b.add_trace(go.Bar(x=mois, y=list(prod_pv_m), marker_color="#E8A33D", name="Production PV (kWh)"))
    fig_b.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8FAFC",
        font=dict(family="Inter"), height=300, margin=dict(l=10,r=10,t=10,b=10),
        title="Production PV mensuelle (kWh)")
    st.plotly_chart(fig_b, use_container_width=True)

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

    # Données matérielles et câblage pour le rapport PDF
    p_cat_pdf = charger_catalogue("panneaux")
    o_cat_pdf = charger_catalogue("onduleurs")
    b_cat_pdf = charger_catalogue("batteries")
    
    p_choisi_pdf = next((p for p in p_cat_pdf if p["id"] == st.session_state.get("panneau_choisi_id")), None) if p_cat_pdf else None
    o_choisi_pdf = next((o for o in o_cat_pdf if o["id"] == st.session_state.get("onduleur_choisi_id")), None) if o_cat_pdf else None
    b_choisi_pdf = next((b for b in b_cat_pdf if b["id"] == st.session_state.get("batterie_choisie_id")), None) if b_cat_pdf and st.session_state.get("inclure_batterie") else None
    
    panneaux_par_pan_pdf = st.session_state.get("panneaux_par_pan", {})
    nb_tot_pv_pdf = sum(panneaux_par_pan_pdf.values()) if isinstance(panneaux_par_pan_pdf, dict) else 0
    
    dist_toit_pdf = float(st.session_state.get("distance_toit_onduleur", 15.0))
    section_dc_pdf = estimer_section_cable(courant_a=12.5, longueur_m=dist_toit_pdf, chute_tension_max_pct=3.0, tension_v=400.0)
    metrages_pdf = estimer_metrage_cablage(nb_panneaux=nb_tot_pv_pdf, distance_toit_onduleur_m=dist_toit_pdf)

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
            "panneau": p_choisi_pdf,
            "onduleur": o_choisi_pdf,
            "batterie": b_choisi_pdf,
            "nb_panneaux": nb_tot_pv_pdf
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
            "pose_fact": float(st.session_state.get("forfait_pose_installation", 2500.0)),
            "thermique_fact": capex_th_r,
            "batterie_fact": capex_bat_r
        },
        "dimensionnement": {
            "surface_m2": st.session_state.get("surface_m2", 120.0),
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
        "prenom": st.session_state.get("client_prenom","Albert"),
        "nom":    st.session_state.get("client_nom","Mercier"),
        "email":  st.session_state.get("client_email",""),
        "societe":st.session_state.get("client_societe",""),
        "adresse":st.session_state.get("adresse_formatee","—"),
        "notes":  st.session_state.get("client_notes",""),
        "installateur_nom": st.session_state.get("installateur_nom","EcoDim Pro"),
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
                    file_name=f"Rapport_EcoDimPro_{client_n.replace(' ','_')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Erreur génération : {e}")

    st.caption(f"⚠️ {DISCLAIMER_DPE}")

# ─── Auto-save ────────────────────────────────────────────────────────────────
_sauvegarder()
