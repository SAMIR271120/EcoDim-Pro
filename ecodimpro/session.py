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


def get_default_etude(nom_etude="Dossier Initial", client_prenom="Albert", client_nom="Mercier") -> dict:
    """Retourne un dictionnaire avec les valeurs par défaut d'un nouveau dossier d'étude."""
    return {
        "nom_etude": nom_etude,
        "installateur_nom": "EcoDim Pro",
        "client_prenom": client_prenom,
        "client_nom": client_nom,
        "client_email": "albert.mercier@email.com",
        "client_societe": "",
        "client_notes": "",
        "adresse_formatee": "14 Avenue verte, Bordeaux",
        "logo_bytes": None,
        "logo_temp_path": None,
        "maison_bytes": None,
        "maison_temp_path": None,
        "latitude": 44.8378,
        "longitude": -0.5792,
        "geocode_success": True,
        "surface_m2": 120.0,
        "niveau_isolation": "bon",
        "periode_construction": "1989–1999",    # période par défaut
        "t_consigne": 19.0,
        "dju_manuel": False,
        "dju_val": 1750.0,
        "mode_elec": "Liste des appareils",
        "appareils_list": [
            {"nom": "Réfrigérateur-Congélateur", "puissance_w": 250.0, "heures_jour": 24.0, "jours_semaine": 7.0},
            {"nom": "Lave-vaisselle", "puissance_w": 1800.0, "heures_jour": 1.2, "jours_semaine": 5.0},
            {"nom": "Lave-linge", "puissance_w": 2000.0, "heures_jour": 1.0, "jours_semaine": 4.0},
            {"nom": "Four électrique", "puissance_w": 2500.0, "heures_jour": 0.5, "jours_semaine": 7.0},
            {"nom": "Téléviseur principal", "puissance_w": 100.0, "heures_jour": 4.0, "jours_semaine": 7.0},
            {"nom": "Ordinateur portable", "puissance_w": 60.0, "heures_jour": 8.0, "jours_semaine": 5.0},
            {"nom": "Éclairage LED & Veilles", "puissance_w": 150.0, "heures_jour": 6.0, "jours_semaine": 7.0},
        ],
        "conso_horaire_csv": None,
        "elec_annuel_kwh": 3527.2,
        "nb_personnes": 4,
        "ecs_mode_conventionnel": True,         # mode DPE conventionnel par défaut
        "litres_par_pers": 56.0,               # valeur réglementaire DPE
        "t_eau_froide": 12.0,
        "t_eau_chaude": 40.0,                  # 40°C = référence DPE
        "inclure_chauffage": True,
        "kwp_pvgis": 3.0,
        "inclinaison_pv": 30,
        "azimut_pv": 0,
        "pr_pv": 0.85,
        "surface_th": 4.0,
        "rendement_th": 0.50,
        "inclure_batterie": False,
        "capacite_bat": 5.0,
        "rendement_bat": 0.90,
        "reseau_type": "230V monophasé",
        "cos_phi": 0.95,
        "injection_limite_active": False,
        "injection_limite_kw": 3.0,
        "station_meteo": "Base PVGIS (non simulé)",
        "prix_reseau": 0.2516,
        "tarif_rachat": 0.13,
        "duree_financement": 20,
        "taux_act": 0.03,
        "prix_pv_kwp": 1900.0,
        "prix_th_m2": 700.0,
        "prix_bat_kwh": 600.0,
        "pans_toiture": [
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
        ],
        "distance_toit_onduleur": 15.0,
        "panneau_choisi_id": "pv_std_425",
        "onduleur_choisi_id": "ond_string_3kw",
        "batterie_choisie_id": "bat_lfp_5",
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
    idx = st_session_state.get("active_etude_idx", 0)
    if "etudes" in st_session_state and idx < len(st_session_state["etudes"]):
        etude = st_session_state["etudes"][idx]
        for key in KEYS_ETUDE:
            if key in st_session_state:
                etude[key] = st_session_state[key]


def init_session(st_session_state):
    """Initialise la session si elle n'existe pas encore (premier chargement)."""
    if "etudes" not in st_session_state:
        from ecodimpro.session import get_default_etude
        st_session_state["etudes"] = [get_default_etude()]
        st_session_state["active_etude_idx"] = 0
        charger_etude(st_session_state, 0)
