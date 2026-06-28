import os
import hashlib
import json
from pathlib import Path
import pandas as pd
import requests

# Base URL pour PVGIS v5.2
PVGIS_API_URL = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"
CACHE_DIR = Path("data/pvgis_cache")

# Heuristique géographique pour la France métropolitaine
def detecter_zone_climatique(latitude: float, longitude: float) -> str:
    """
    Détermine la zone climatique (H1, H2, H3) d'après les coordonnées GPS.
    """
    if latitude > 46.5:
        if longitude > 2.0:
            return "H1"
        else:
            return "H2"
    elif latitude > 44.5:
        return "H2"
    else:
        return "H3"

# Table de fallback d'irradiation mensuelle moyenne (kWh/m²/mois)
FALLBACK_IRRADIATION = {
    # Annuel ~1100 kWh/m²
    "H1": [35.0, 50.0, 85.0, 115.0, 140.0, 155.0, 160.0, 135.0, 100.0, 65.0, 40.0, 25.0],
    # Annuel ~1300 kWh/m²
    "H2": [40.0, 60.0, 100.0, 135.0, 165.0, 180.0, 185.0, 160.0, 120.0, 75.0, 48.0, 32.0],
    # Annuel ~1600 kWh/m²
    "H3": [60.0, 80.0, 125.0, 165.0, 200.0, 220.0, 225.0, 195.0, 150.0, 98.0, 62.0, 50.0]
}

DAYS_IN_MONTH = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

def _normaliser_data(data: dict) -> dict:
    """
    Garantit que data['outputs']['monthly'] est une liste de dictionnaires.
    Si c'est un dictionnaire (provenant de l'API réelle PVGIS), on extrait la liste
    qui se trouve sous une clé (ex: 'fixed').
    """
    if "outputs" in data and "monthly" in data["outputs"]:
        monthly = data["outputs"]["monthly"]
        if isinstance(monthly, dict):
            for val in monthly.values():
                if isinstance(val, list):
                    data["outputs"]["monthly"] = val
                    break
    return data

def recuperer_irradiation_pvgis(latitude: float, longitude: float, inclinaison: float = 30, azimut: float = 0) -> dict:
    """
    Appelle l'API PVGIS pour récupérer la production et l'irradiation mensuelles.
    Met en cache le résultat JSON localement.
    En cas de panne réseau, renvoie les données de fallback pour la zone climatique détectée.
    """
    # Normalisation des paramètres pour la clé de cache
    lat_key = f"{latitude:.4f}"
    lon_key = f"{longitude:.4f}"
    inc_key = f"{inclinaison:.1f}"
    azi_key = f"{azimut:.1f}"
    
    param_str = f"lat={lat_key}_lon={lon_key}_inc={inc_key}_azi={azi_key}"
    hash_key = hashlib.md5(param_str.encode("utf-8")).hexdigest()
    
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"pvgis_{hash_key}.json"
    
    # 1. Vérification du cache
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return _normaliser_data(data)
        except Exception:
            pass  # Si le fichier de cache est corrompu, on poursuit vers l'API
            
    # 2. Requête API
    params = {
        "lat": lat_key,
        "lon": lon_key,
        "peakpower": 1,
        "loss": 14,
        "angle": inc_key,
        "aspect": azi_key,
        "outputformat": "json"
    }
    
    try:
        response = requests.get(PVGIS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        data = _normaliser_data(data)
        
        # Enregistrement dans le cache
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return data
        
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        # 3. Fallback en cas d'erreur
        zone = detecter_zone_climatique(latitude, longitude)
        monthly_irrad = FALLBACK_IRRADIATION[zone]
        
        fallback_data = {
            "outputs": {
                "monthly": [
                    {
                        "month": m,
                        "E_m": h_val * 0.86, # Rendement avec 14% de pertes
                        "E_d": (h_val * 0.86) / DAYS_IN_MONTH[m],
                        "H(i)_d": h_val / DAYS_IN_MONTH[m]
                    }
                    for m, h_val in enumerate(monthly_irrad, start=1)
                ]
            },
            "meta": {
                "source": "fallback",
                "zone_climatique": zone,
                "msg": "Données estimées suite à l'indisponibilité du service PVGIS."
            }
        }
        return fallback_data

def production_pv_mensuelle(latitude: float, longitude: float, kwp: float, inclinaison: float = 30, azimut: float = 0, performance_ratio: float = 0.85) -> pd.Series:
    """
    Calcule la production PV mensuelle en kWh pour une installation de puissance `kwp`
    et un `performance_ratio` donné.
    Retourne une série pandas de 12 valeurs (index 1 à 12).
    """
    data = recuperer_irradiation_pvgis(latitude, longitude, inclinaison, azimut)
    monthly_data = data.get("outputs", {}).get("monthly", [])
    
    prod_dict = {}
    for m_data in monthly_data:
        m = int(m_data["month"])
        e_m = float(m_data["E_m"])  # Production mensuelle pour 1 kWp à 14% pertes (PR = 0.86)
        
        # Ajustement par rapport au kwp et au performance_ratio ciblé
        # e_m est pour 1 kWp et 14% de pertes (PR = 0.86)
        # On remplace les pertes de 14% par le performance_ratio passé en paramètre
        prod_kwh = e_m * kwp * (performance_ratio / 0.86)
        prod_dict[m] = prod_kwh
        
    return pd.Series(prod_dict)

def production_pv_annuelle(latitude: float, longitude: float, kwp: float, inclinaison: float = 30, azimut: float = 0, performance_ratio: float = 0.85) -> float:
    """
    Calcule la production PV annuelle totale en kWh.
    """
    prod_mensuelle = production_pv_mensuelle(latitude, longitude, kwp, inclinaison, azimut, performance_ratio)
    return float(prod_mensuelle.sum())


def calculer_nb_panneaux_max(surface_utile_m2: float, panneau: dict, facteur_foisonnement: float = 0.85) -> int:
    """
    Calcule le nombre maximum de panneaux installables sur une surface utile donnée
    en tenant compte du coefficient de foisonnement (espacement, service, sécurité).
    nb_panneaux = floor(surface_utile_m2 * facteur_foisonnement / surface_panneau)
    """
    import math
    if not panneau or "surface_m2" not in panneau:
        return 0
    surface_p = panneau["surface_m2"]
    if surface_p <= 0.0:
        return 0
    return math.floor((surface_utile_m2 * facteur_foisonnement) / surface_p)


def puissance_totale_kwc(nb_panneaux: int, panneau: dict) -> float:
    """
    Calcule la puissance crête totale (kWc) d'un ensemble de panneaux.
    Puissance (kWc) = nb_panneaux * puissance_wc_panneau / 1000
    """
    if not panneau or "puissance_wc" not in panneau:
        return 0.0
    p_wc = panneau["puissance_wc"]
    return max(0, nb_panneaux) * p_wc / 1000.0
