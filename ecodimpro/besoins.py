import os
from pathlib import Path
from typing import Union
import pandas as pd

from ecodimpro.constantes_dpe import DH14_PAR_ZONE, DJU_BASE18_PAR_ZONE

def calc_besoin_elec(appareils: Union[list[dict], str, Path]) -> Union[float, tuple[float, pd.Series]]:
    """
    Calcule la consommation électrique annuelle en kWh.
    
    Si `appareils` est une liste de dictionnaires :
        Chaque dictionnaire doit contenir :
        - 'puissance_w': puissance de l'appareil en W
        - 'heures_jour': heures d'utilisation par jour
        - 'jours_semaine': jours d'utilisation par semaine
        Retourne la consommation annuelle brute en kWh (float).
        
    Si `appareils` est un chemin vers un fichier CSV :
        Le CSV doit contenir une colonne d'horodatage et une colonne de consommation (kWh).
        Retourne un tuple (somme_annuelle, serie_horaire) où serie_horaire est une série pandas
        indexée par date, représentant la consommation horaire.
    """
    if isinstance(appareils, (str, Path)):
        filepath = Path(appareils)
        if not filepath.exists():
            raise FileNotFoundError(f"Le fichier CSV {filepath} n'existe pas.")
        
        df = pd.read_csv(filepath)
        
        # Identification de la colonne de temps
        time_col = None
        for col in df.columns:
            if any(x in col.lower() for x in ["timestamp", "time", "date", "horodatage"]):
                time_col = col
                break
        
        # Identification de la colonne de consommation
        conso_col = None
        for col in df.columns:
            if any(x in col.lower() for x in ["conso", "kwh", "val", "value", "puissance"]):
                conso_col = col
                break
                
        if time_col is None or conso_col is None:
            raise ValueError(
                "Le CSV doit contenir au moins une colonne pour le temps (date/time/horodatage) "
                "et une colonne pour la consommation (conso/kwh/value)."
            )
            
        # Conversion du temps et tri
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.sort_values(by=time_col)
        df.set_index(time_col, inplace=True)
        
        # Assurer que la série est bien de type numérique
        series = pd.to_numeric(df[conso_col], errors="coerce").fillna(0.0)
        
        # Resampling horaire pour garantir une série horaire homogène
        serie_horaire = series.resample("h").sum()
        somme_annuelle = serie_horaire.sum()
        
        return somme_annuelle, serie_horaire

    elif isinstance(appareils, list):
        total_kwh = 0.0
        for app in appareils:
            puissance = float(app.get("puissance_w", 0.0))
            heures = float(app.get("heures_jour", 0.0))
            jours = float(app.get("jours_semaine", 0.0))
            # Formule : puissance_w/1000 * heures_jour * jours_semaine * 52.14
            total_kwh += (puissance / 1000.0) * heures * jours * 52.14
        return total_kwh
    else:
        raise TypeError("L'argument 'appareils' doit être une liste de dictionnaires ou un chemin vers un fichier CSV.")

def calc_besoin_ecs(
    nb_personnes: int,
    litres_par_jour_par_personne: float = 56.0,
    t_entree: float = 12.0,
    t_sortie: float = 40.0
) -> float:
    """
    Calcule l’énergie annuelle nécessaire pour l’eau chaude sanitaire (ECS) en kWh/an.

    Valeurs par défaut conformément à la méthode 3CL-DPE (arrêté 31 mars 2021) :
      - 56 L/jour/personne à 40°C (usage conventionnel DPE).
    Pour un usage personnalisé, passer litres_par_jour_par_personne et t_sortie manuellement.

    Formule physique :
    E (kWh/an) = nb_personnes * litres/j/pers * 365 * (t_sortie - t_entree) * 1.163 / 1000
    """
    if nb_personnes <= 0:
        return 0.0

    energie_kwh = (
        nb_personnes *
        litres_par_jour_par_personne *
        365 *
        (t_sortie - t_entree) *
        1.163 / 1000.0
    )
    return energie_kwh

def calc_besoin_chauffage(
    surface_m2: float,
    umur: float,
    uph: float,
    upb: float = 0.45,
    dh14: float = 33_300.0,
    surface_murs_pct: float = 0.6,
    surface_toiture_pct: float = 0.3,
    surface_plancher_pct: float = 0.1,
) -> float:
    """
    Estimation du besoin de chauffage annuel (kWh/an) basée sur les coefficients U
    réglementaires de la méthode 3CL-DPE (arrêté du 31 mars 2021).

    IMPORTANT — Simplification pédagogique :
    Cette formule répartit la surface habitable entre murs, toiture et plancher selon
    des ratios par défaut (murs 60 %, toiture 30 %, plancher 10 %). Elle utilise ensuite
    les coefficients U officiels et les Degrés-Heures base 14 °C (DH14) de la zone
    climatique pour calculer une estimation des déperditions thermiques annuelles.
    
    Cette approche est cohérente avec la méthode 3CL-DPE mais constitue une SIMPLIFICATION.
    Elle ne prend pas en compte : la géométrie exacte des parois, les ponts thermiques,
    la ventilation, les apports solaires ni les occupants. Elle ne se substitue pas à un
    diagnostic de performance énergétique (DPE) officiel réalisé par un diagnostiqueur
    certifié conformément à l'arrêté du 31 mars 2021.

    Formule :
        GV (W/K) = umur × S_murs + uph × S_toiture + upb × S_plancher
        Besoin (kWh/an) = GV × DH14 / 1000

    Paramètres :
        surface_m2          : Surface habitable (m²)
        umur                : Coefficient U des murs (W/m²·K) — voir UMUR_PAR_PERIODE
        uph                 : Coefficient U de la toiture/combles (W/m²·K) — voir UPH_TOITURE
        upb                 : Coefficient U du plancher bas (W/m²·K) — défaut 0.45 W/m²·K
        dh14                : Degrés-Heures base 14°C de la zone — voir ZONES_CLIMATIQUES
        surface_murs_pct    : Part de la surface affectée aux murs (défaut 0.6)
        surface_toiture_pct : Part de la surface affectée à la toiture (défaut 0.3)
        surface_plancher_pct: Part de la surface affectée au plancher (défaut 0.1)
    """
    s_murs     = surface_m2 * surface_murs_pct
    s_toiture  = surface_m2 * surface_toiture_pct
    s_plancher = surface_m2 * surface_plancher_pct

    gv_wk = umur * s_murs + uph * s_toiture + upb * s_plancher
    besoin_kwh = gv_wk * dh14 / 1000.0
    return besoin_kwh


def calc_besoin_chauffage_legacy(
    surface_m2: float,
    niveau_isolation: str,
    deg_jours_unifies: float = None,
    t_consigne: float = 19,
    zone_climatique: str = "H2",
    utiliser_dh14: bool = False,
) -> float:
    """
    Ancienne formule de calcul du besoin de chauffage (conservée pour compatibilité).
    Utilise un coefficient G global (W/m²·K) selon le niveau d'isolation.
    Préférer calc_besoin_chauffage() qui utilise les vrais coefficients U 3CL-DPE.

    niveau_isolation : 'faible', 'moyen', 'bon', 'rt2012'
    deg_jours_unifies : Si non fourni, estimé à partir de la zone climatique.
    t_consigne : température de consigne (défaut 19°C)
    zone_climatique : 'H1', 'H2' ou 'H3'
    utiliser_dh14 : Si True, utilise les DH14 (DJU ≈ DH14 / 24)
    """
    isolation_map = {
        "faible": 2.5,
        "moyen":  1.5,
        "bon":    1.0,
        "rt2012": 0.6,
    }
    g_val = isolation_map.get(niveau_isolation.lower(), 1.5)

    if deg_jours_unifies is not None:
        dju_base = float(deg_jours_unifies)
    elif utiliser_dh14:
        dh14_val = DH14_PAR_ZONE.get(zone_climatique.upper(), DH14_PAR_ZONE["H2"])
        dju_base = dh14_val / 24.0
    else:
        dju_base = DJU_BASE18_PAR_ZONE.get(zone_climatique.upper(), DJU_BASE18_PAR_ZONE["H2"])

    dju_corrige = dju_base + (t_consigne - 18.0) * 200.0
    dju_corrige = max(0.0, dju_corrige)

    besoin_kwh = surface_m2 * g_val * dju_corrige * 24.0 / 1000.0
    return besoin_kwh

    """
    Calcule le besoin de chauffage annuel en kWh/an par la méthode des degrés-jours.

    niveau_isolation : 'faible', 'moyen', 'bon', 'rt2012'
    deg_jours_unifies : Si non fourni, estimé à partir de la zone climatique (H1, H2, H3).
    t_consigne : température de consigne souhaitée (défaut 19°C)
    zone_climatique : 'H1' (Nord/Est), 'H2' (Ouest/Centre), 'H3' (Méditerranée)
    utiliser_dh14 : Si True, utilise les Dégrés-Heures base 14°C (méthode 3CL-DPE officielle).
                    Les DH14 sont conver tis en DJUéquivalents avant calcul.
    """
    # Mapping niveau d'isolation -> coefficient de déperdition G en W/m²/°C
    isolation_map = {
        "faible": 2.5,
        "moyen":  1.5,
        "bon":    1.0,
        "rt2012": 0.6,
    }
    g_val = isolation_map.get(niveau_isolation.lower(), 1.5)

    # Base DJU
    if deg_jours_unifies is not None:
        dju_base = float(deg_jours_unifies)
    elif utiliser_dh14:
        # Conversion DH14 -> DJUéquivalent (base 18°C) : DJU ≈ DH14 / 24
        dh14 = DH14_PAR_ZONE.get(zone_climatique.upper(), DH14_PAR_ZONE["H2"])
        dju_base = dh14 / 24.0
    else:
        dju_base = DJU_BASE18_PAR_ZONE.get(zone_climatique.upper(), DJU_BASE18_PAR_ZONE["H2"])

    # Ajustement des DJU selon la température de consigne
    # Base standard des DJU = 18°C. On ajoute (t_consigne - 18) * 200 jours de chauffe.
    dju_corrige = dju_base + (t_consigne - 18.0) * 200.0
    dju_corrige = max(0.0, dju_corrige)

    # Formule : besoin (kWh/an) = surface_m2 * G * dju_corrige * 24 / 1000
    besoin_kwh = surface_m2 * g_val * dju_corrige * 24.0 / 1000.0
    return besoin_kwh
