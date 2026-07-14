"""
ecodimpro/constantes_dpe.py
Constantes réglementaires officielles — méthode 3CL-DPE
Arrêté du 31 mars 2021 (méthode de calcul de la performance énergétique des logements)
"""

# ─────────────────────────────────────────────────────────────────────────────
# Degrés-Heures base 14 °C (DH14) par zone climatique — arrêté 31 mars 2021
# Utilisés dans la méthode 3CL-DPE pour le calcul des besoins de chauffage
# ─────────────────────────────────────────────────────────────────────────────
DH14_PAR_ZONE: dict[str, float] = {
    "H1": 42_030.0,   # Nord / Est / Montagne — climat le plus rigoureux
    "H2": 33_300.0,   # Ouest / Centre / Sud-Ouest — climat tempéré
    "H3": 22_200.0,   # Méditerranée — climat le plus doux
}

# Valeurs DJU (Degrés-Jours Unifiés, base 18 °C) de référence par zone
# Source : ADEME / CSTB (valeurs courantes utilisées en simulation)
DJU_BASE18_PAR_ZONE: dict[str, float] = {
    "H1": 2_600.0,
    "H2": 2_000.0,
    "H3": 1_400.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# Valeurs DPE conventionnelles pour l'ECS — arrêté 31 mars 2021, annexe I
# ─────────────────────────────────────────────────────────────────────────────
ECS_LITRES_CONVENTIONNEL: float = 56.0    # L/jour/personne à 40 °C (usage conventionnel)
ECS_TEMP_CHAUDE_CONVENTIONNEL: float = 40.0   # °C — température de puisage de référence DPE
ECS_TEMP_FROIDE_REFERENCE: float = 12.0        # °C — température eau froide de référence

# ─────────────────────────────────────────────────────────────────────────────
# Coefficients U (W/m²·K) par période de construction
# Source : Annexe 7 de l'arrêté du 31 mars 2021 relatif au DPE
# Ces valeurs sont les moyennes réglementaires par paroi type
# ─────────────────────────────────────────────────────────────────────────────
U_PAR_PERIODE: dict[str, dict[str, float]] = {
    "Avant 1948": {
        "u_mur": 2.50,
        "u_toiture": 2.50,
        "u_plancher_bas": 2.00,
        "u_fenetre": 4.25,
    },
    "1948–1974": {
        "u_mur": 2.00,
        "u_toiture": 1.50,
        "u_plancher_bas": 2.00,
        "u_fenetre": 4.25,
    },
    "1975–1977": {
        "u_mur": 0.56,
        "u_toiture": 0.43,
        "u_plancher_bas": 0.45,
        "u_fenetre": 3.30,
    },
    "1978–1981": {
        "u_mur": 0.56,
        "u_toiture": 0.43,
        "u_plancher_bas": 0.45,
        "u_fenetre": 3.30,
    },
    "1982–1988": {
        "u_mur": 0.45,
        "u_toiture": 0.43,
        "u_plancher_bas": 0.45,
        "u_fenetre": 3.30,
    },
    "1989–1999": {
        "u_mur": 0.45,
        "u_toiture": 0.26,
        "u_plancher_bas": 0.36,
        "u_fenetre": 3.30,
    },
    "2000–2005": {
        "u_mur": 0.36,
        "u_toiture": 0.26,
        "u_plancher_bas": 0.27,
        "u_fenetre": 2.90,
    },
    "2006–2012": {
        "u_mur": 0.27,
        "u_toiture": 0.20,
        "u_plancher_bas": 0.27,
        "u_fenetre": 2.40,
    },
    "2012–2021 (RT2012)": {
        "u_mur": 0.20,
        "u_toiture": 0.20,
        "u_plancher_bas": 0.20,
        "u_fenetre": 1.80,
    },
    "2021+ (RE2020)": {
        "u_mur": 0.15,
        "u_toiture": 0.13,
        "u_plancher_bas": 0.15,
        "u_fenetre": 1.30,
    },
}

# Liste triée des périodes (dans l'ordre chronologique)
PERIODES_CONSTRUCTION: list[str] = list(U_PAR_PERIODE.keys())

# ─────────────────────────────────────────────────────────────────────────────
# Correspondance : période → niveau d'isolation (pour calc_besoin_chauffage)
# Mapping simplifié — G (W/m²·K) global estimé à partir de l'U moyen
# ─────────────────────────────────────────────────────────────────────────────
PERIODE_TO_ISOLATION: dict[str, str] = {
    "Avant 1948":         "faible",
    "1948–1974":          "faible",
    "1975–1977":          "moyen",
    "1978–1981":          "moyen",
    "1982–1988":          "moyen",
    "1989–1999":          "bon",
    "2000–2005":          "bon",
    "2006–2012":          "bon",
    "2012–2021 (RT2012)": "rt2012",
    "2021+ (RE2020)":     "rt2012",
}

# Labels lisibles pour l'interface (sélecteur)
LABELS_ISOLATION: dict[str, str] = {
    "faible":  "Faible — Logement ancien non isolé (G ≈ 2.5 W/m²K)",
    "moyen":   "Moyen — Isolation 1ère génération (G ≈ 1.5 W/m²K)",
    "bon":     "Bon — Isolation moderne (G ≈ 1.0 W/m²K)",
    "rt2012":  "Excellent — RT2012 / RE2020 (G ≈ 0.6 W/m²K)",
}

# =============================================================================
# NOUVEAUX PARAMÈTRES RÉGLEMENTAIRES (arrêté 31 mars 2021 + méthode 3CL-DPE)
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# Scénarios d'usage ECS — litres/jour/personne (méthode 3CL-DPE)
# ─────────────────────────────────────────────────────────────────────────────
SCENARIOS_ECS: dict[str, float] = {
    "Conventionnel (réglementaire — 3CL-DPE)": 56.0,   # valeur officielle arrêté 31/03/2021
    "Usage dépensier":                          79.0,   # profil intense (réf. CSTB)
    "Saisie manuelle":                         None,    # l'utilisateur entre la valeur librement
}

# ─────────────────────────────────────────────────────────────────────────────
# Zones climatiques officielles — Tmoy et DH14 (Degrés-Heures base 14°C)
# Arrêté du 31 mars 2021 relatif au DPE — annexe 1
# ─────────────────────────────────────────────────────────────────────────────
ZONES_CLIMATIQUES: dict[str, dict] = {
    "H1": {
        "label":  "H1 — Nord / Est / Montagne (climat le plus rigoureux)",
        "tmoy":    6.58,
        "dh14": 42_030.0,
    },
    "H2": {
        "label":  "H2 — Ouest / Centre / Sud-Ouest (climat tempéré)",
        "tmoy":    8.08,
        "dh14": 33_300.0,
    },
    "H3": {
        "label":  "H3 — Méditerranée (climat le plus doux)",
        "tmoy":    9.65,
        "dh14": 22_200.0,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Coefficients U mur (W/m²·K) par période et zone climatique
# Source : Annexe 7 arrêté 31 mars 2021 — isolation par l'intérieur (ITE/ITI)
# ─────────────────────────────────────────────────────────────────────────────
UMUR_PAR_PERIODE: dict[str, dict] = {
    "Non isolé (avant 1975)": {
        "H1": 2.50, "H2": 2.50, "H3": 2.50,
        "label": "Non isolé (avant 1975) — U ≈ 2.50 W/m²K",
    },
    "Isolé 1975–1977": {
        "H1": 0.50, "H2": 0.53, "H3": 0.56,
        "label": "Isolé 1975–1977 — U ≈ 0.50–0.56 W/m²K selon zone",
    },
    "Isolé 1978–1982": {
        "H1": 0.40, "H2": 0.42, "H3": 0.44,
        "label": "Isolé 1978–1982 — U ≈ 0.40–0.44 W/m²K selon zone",
    },
    "Isolé 1983–1988": {
        "H1": 0.30, "H2": 0.32, "H3": 0.33,
        "label": "Isolé 1983–1988 — U ≈ 0.30–0.33 W/m²K selon zone",
    },
    "Isolé 1989–2000": {
        "H1": 0.25, "H2": 0.26, "H3": 0.30,
        "label": "Isolé 1989–2000 — U ≈ 0.25–0.30 W/m²K selon zone",
    },
    "Isolé 2001–2005": {
        "H1": 0.23, "H2": 0.23, "H3": 0.30,
        "label": "Isolé 2001–2005 — U ≈ 0.23–0.30 W/m²K selon zone",
    },
    "Isolé à partir de 2006": {
        "H1": 0.20, "H2": 0.20, "H3": 0.25,
        "label": "Isolé à partir de 2006 — U ≈ 0.20–0.25 W/m²K selon zone",
    },
}

PERIODES_UMUR: list[str] = list(UMUR_PAR_PERIODE.keys())

# ─────────────────────────────────────────────────────────────────────────────
# Coefficients Uph toiture / combles (W/m²·K)
# Source : Annexe 7 arrêté 31 mars 2021 — isolation combles et toiture-terrasse
# ─────────────────────────────────────────────────────────────────────────────
UPH_TOITURE: dict[str, float] = {
    "Combles perdus, isolés jusqu'en 1988":      0.43,
    "Combles perdus, isolés 1989–2000":          0.23,
    "Combles perdus, isolés à partir de 2000":   0.19,
    "Combles aménagés, isolés jusqu'en 1988":    0.61,
    "Combles aménagés, isolés 1989–2000":        0.38,
    "Combles aménagés, isolés à partir de 2000": 0.27,
    "Toiture-terrasse, isolée jusqu'en 1988":    1.00,
    "Toiture-terrasse, isolée 1989–2000":        0.50,
    "Toiture-terrasse, isolée à partir de 2000": 0.30,
}

TYPES_TOITURE: list[str] = list(UPH_TOITURE.keys())

# ─────────────────────────────────────────────────────────────────────────────
# Coefficient Upb plancher bas (W/m²·K)
# Valeur officielle par défaut — plancher bas sur vide sanitaire ou terre-plein
# ─────────────────────────────────────────────────────────────────────────────
UPB_PLANCHER_BAS_DEFAUT: float = 0.45   # W/m²·K — arrêté 31/03/2021 annexe 7
