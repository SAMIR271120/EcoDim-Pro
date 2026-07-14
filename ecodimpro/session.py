"""
ecodimpro/session.py
Gestion centralisée de l'état de session multi-pages Streamlit.
Contient les clés, les valeurs par défaut, et les fonctions de chargement/sauvegarde.
"""

# Clés de l'étude : tout ce qui constitue un dossier complet
KEYS_ETUDE = [
    "nom_etude", "installateur_nom", "client_prenom", "client_nom", "client_email",
    "client_societe", "client_notes", "adresse_formatee", "logo_bytes", "logo_temp_path",
    "maison_bytes", "maison_temp_path",
    "latitude", "longitude", "geocode_success", "surface_m2", "niveau_isolation",
    "periode_construction",                     # [NOUVEAU] période de construction
    "t_consigne", "dju_manuel", "dju_val", "mode_elec", "appareils_list",
    "conso_horaire_csv", "elec_annuel_kwh", "nb_personnes",
    "ecs_mode_conventionnel",                   # [NOUVEAU] mode ECS conventionnel DPE
    "litres_par_pers", "t_eau_froide", "t_eau_chaude",
    "inclure_chauffage", "kwp_pvgis", "inclinaison_pv", "azimut_pv",
    "pr_pv", "surface_th", "rendement_th", "inclure_batterie", "capacite_bat",
    "rendement_bat", "reseau_type", "cos_phi", "injection_limite_active", "injection_limite_kw",
    "station_meteo", "prix_reseau", "tarif_rachat", "duree_financement", "taux_act",
    "prix_pv_kwp", "prix_th_m2", "prix_bat_kwh",
    "pans_toiture", "distance_toit_onduleur", "panneau_choisi_id",
    "onduleur_choisi_id", "batterie_choisie_id", "panneaux_par_pan"
]


def get_default_etude(nom_etude="", client_prenom="", client_nom="") -> dict:
    """Retourne un dictionnaire vierge pour un nouveau dossier d'étude.
    Aucune valeur factice ou exemple n'est pré-rempli : tout est vide/zéro.
    """
    return {
        "nom_etude": nom_etude,
        "installateur_nom": "",
        "client_prenom": client_prenom,
        "client_nom": client_nom,
        "client_email": "",
        "client_societe": "",
        "client_notes": "",
        "adresse_formatee": "",
        "logo_bytes": None,
        "logo_temp_path": None,
        "maison_bytes": None,
        "maison_temp_path": None,
        "latitude": 0.0,
        "longitude": 0.0,
        "geocode_success": False,
        "surface_m2": 0.0,
        "niveau_isolation": None,
        "periode_construction": None,
        "t_consigne": 19.0,        # valeur physique de référence (pas une donnée client)
        "dju_manuel": False,
        "dju_val": 0.0,
        "mode_elec": "Consommation annuelle",
        "appareils_list": [],
        "conso_horaire_csv": None,
        "elec_annuel_kwh": 0.0,
        "nb_personnes": 0,
        "ecs_mode_conventionnel": True,
        "litres_par_pers": 0.0,
        "t_eau_froide": 0.0,
        "t_eau_chaude": 0.0,
        "inclure_chauffage": False,
        "kwp_pvgis": 0.0,
        "inclinaison_pv": 0,
        "azimut_pv": 0,
        "pr_pv": 0.85,             # constante technique standard PV
        "surface_th": 0.0,
        "rendement_th": 0.0,
        "inclure_batterie": False,
        "capacite_bat": 0.0,
        "rendement_bat": 0.0,
        "reseau_type": "230V monophasé",
        "cos_phi": 1.0,
        "injection_limite_active": False,
        "injection_limite_kw": 0.0,
        "station_meteo": "",
        "prix_reseau": 0.0,
        "tarif_rachat": 0.0,
        "duree_financement": 0,
        "taux_act": 0.0,
        "prix_pv_kwp": 0.0,
        "prix_th_m2": 0.0,
        "prix_bat_kwh": 0.0,
        "pans_toiture": [],
        "distance_toit_onduleur": 0.0,
        "panneau_choisi_id": None,
        "onduleur_choisi_id": None,
        "batterie_choisie_id": None,
        "panneaux_par_pan": {},
    }


def charger_etude(st_session_state, idx: int):
    """Copie les valeurs du dossier `idx` dans st.session_state."""
    etude = st_session_state["etudes"][idx]
    for key in KEYS_ETUDE:
        if key in etude:
            st_session_state[key] = etude[key]


def sauvegarder_etude_courante(st_session_state):
    """Copie les valeurs courantes de st.session_state dans le dossier actif."""
    idx = st_session_state.get("active_etude_idx")
    if idx is None:
        return  # aucun dossier actif — rien à sauvegarder
    etudes = st_session_state.get("etudes") or []
    if not etudes or int(idx) >= len(etudes):
        return
    etude = etudes[int(idx)]
    for key in KEYS_ETUDE:
        if key in st_session_state:
            etude[key] = st_session_state[key]



def init_session(st_session_state):
    """Initialise la session si elle n'existe pas encore (premier chargement).
    Au démarrage, la liste des dossiers est vide : l'utilisateur crée son premier dossier.
    """
    if "etudes" not in st_session_state:
        st_session_state["etudes"] = []
        st_session_state["active_etude_idx"] = None
        st_session_state["current_step"] = 1
        st_session_state["view_accueil"] = "list"
