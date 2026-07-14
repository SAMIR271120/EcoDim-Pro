"""
ecodimpro/equipements.py
Gestion et filtrage du catalogue d'équipements (panneaux, onduleurs, batteries).
"""
import os
import json
from pathlib import Path
import math

def charger_catalogue(type_equipement: str) -> list[dict]:
    """
    Charge les équipements depuis le catalogue JSON correspondant :
    - type_equipement: 'panneaux', 'onduleurs' ou 'batteries'
    """
    base_dir = Path(__file__).resolve().parent.parent / "data" / "equipements"
    filepath = base_dir / f"{type_equipement}.json"
    
    if not filepath.exists():
        # Fallback si absent ou dossier de test
        return []
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception:
        return []

def filtrer_panneaux_par_surface(catalogue: list[dict], surface_disponible_m2: float, facteur_foisonnement: float = 0.85) -> list[dict]:
    """
    Filtre les panneaux et calcule pour chacun le nombre max installable.
    Retourne la liste des panneaux compatibles (pouvant en installer au moins un)
    avec une clé 'nb_max_panneaux' ajoutée dynamiquement.
    """
    compatibles = []
    for item in catalogue:
        surface_p = item.get("surface_m2")
        if not surface_p:
            # Sécurité au cas où la surface n'est pas renseignée, calcul depuis dimensions
            longueur = item.get("longueur_m", 1.72)
            largeur = item.get("largeur_m", 1.13)
            surface_p = longueur * largeur
            
        nb_max = math.floor((surface_disponible_m2 * facteur_foisonnement) / surface_p)
        if nb_max > 0:
            new_item = item.copy()
            new_item["nb_max_panneaux"] = nb_max
            compatibles.append(new_item)
            
    return compatibles
