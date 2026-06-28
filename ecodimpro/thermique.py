def dimensionner_ballon(litres_jour: float) -> float:
    """
    Calcule le volume recommandé du ballon d'eau chaude (en litres).
    Règle : volume_ballon = 1.5 * litres_jour.
    """
    return 1.5 * max(0.0, litres_jour)

def surface_capteurs_recommandee(nb_personnes: int, zone_climatique: str) -> float:
    """
    Calcule la surface de capteurs thermiques recommandée en m² d'après le nombre de personnes
    et la zone climatique française (H1, H2, H3).
    
    H1 / H2 : 1.5 à 2.0 m²/personne (moyenne 1.75 m²)
    H3 : 1.0 à 1.5 m²/personne (moyenne 1.25 m²)
    """
    nb_p = max(0, nb_personnes)
    if nb_p == 0:
        return 0.0
        
    z = zone_climatique.upper()
    if z in ["H1", "H2"]:
        ratio = 1.75
    elif z == "H3":
        ratio = 1.25
    else:
        ratio = 1.75  # Valeur par défaut si zone non spécifiée/inconnue
        
    return nb_p * ratio

def couverture_ecs(surface_capteurs: float, rendement_capteur: float, besoin_ecs_kwh: float, irradiation_annuelle_kwh_m2: float) -> dict:
    """
    Calcule la production thermique et le taux de couverture solaire pour l'ECS.
    
    production_thermique = surface_capteurs * rendement_capteur * irradiation_annuelle_kwh_m2
    taux_couverture = min(production_thermique / besoin_ecs_kwh, 1.0)
    Plafonné à un maximum réaliste de 80% (0.80) pour l'eau chaude résidentielle.
    Si le taux de couverture brut dépasse 85%, un message d'alerte de stagnation estivale est généré.
    """
    production_thermique = max(0.0, surface_capteurs) * max(0.0, rendement_capteur) * max(0.0, irradiation_annuelle_kwh_m2)
    
    if besoin_ecs_kwh <= 0.0:
        return {
            "production_thermique": production_thermique,
            "taux_couverture": 0.0,
            "energie_appoint": 0.0,
            "warning": "Le besoin ECS est nul."
        }
        
    raw_coverage = production_thermique / besoin_ecs_kwh
    
    # Message d'avertissement de surdimensionnement (stagnation estivale)
    warning = ""
    if raw_coverage > 0.85:
        warning = (
            f"Attention : Le taux de couverture brut ({raw_coverage:.1%}) dépasse 85%. "
            "Il y a un risque élevé de stagnation estivale (surchauffe du fluide caloporteur). "
            "Il est recommandé de réduire la surface de capteurs ou d'ajouter une boucle de décharge."
        )
        
    # Plafonnement réaliste de couverture utile
    taux_couverture = min(raw_coverage, 0.80)
    
    energie_solaire_utile = taux_couverture * besoin_ecs_kwh
    energie_appoint = besoin_ecs_kwh - energie_solaire_utile
    
    return {
        "production_thermique": production_thermique,
        "taux_couverture": taux_couverture,
        "energie_appoint": energie_appoint,
        "warning": warning
    }
