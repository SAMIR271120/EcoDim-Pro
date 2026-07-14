import pandas as pd
from typing import Union

def calc_autoconsommation(
    production_kwh: Union[float, pd.Series], 
    consommation_kwh: Union[float, pd.Series]
) -> dict:
    """
    Calcule le taux d'autoconsommation et le taux d'autonomie.
    
    Si les entrées sont des séries pandas (ex: horaires ou mensuelles) :
        Le calcul est fait par intégration (somme des min(prod, cons) à chaque pas de temps).
    Si ce sont des valeurs flottantes (totaux annuels globaux) :
        On utilise un ratio empirique standard de 35% pour l'autoconsommation résidentielle sans stockage,
        plafonné par la consommation totale du logement.
        
    Retourne un dictionnaire avec :
        - 'taux_autoconsommation': fraction de la production consommée sur place
        - 'taux_autonomie': fraction de la consommation couverte par la production locale
        - 'surplus_kwh': électricité injectée sur le réseau
        - 'energie_achetee_kwh': électricité achetée au réseau
        - 'energie_autoconsommee_kwh': électricité autoproduite et autoconsommée
    """
    # 1. Cas des profils temporels (pandas Series)
    if isinstance(production_kwh, pd.Series) and isinstance(consommation_kwh, pd.Series):
        # Alignement des séries sur le même index
        df = pd.DataFrame({"prod": production_kwh, "cons": consommation_kwh}).fillna(0.0)
        self_consumed_series = df.min(axis=1)
        
        total_self_consumed = float(self_consumed_series.sum())
        total_prod = float(df["prod"].sum())
        total_cons = float(df["cons"].sum())
        
    # 2. Cas des totaux annuels globaux (floats)
    else:
        total_prod = float(production_kwh)
        total_cons = float(consommation_kwh)
        
        # Hypothèse simplifiée : 35% de la production PV est autoconsommée en résidentiel.
        # Plafonné par la consommation totale.
        total_self_consumed = min(total_prod * 0.35, total_cons)
        
    taux_autoconsommation = total_self_consumed / total_prod if total_prod > 0 else 0.0
    taux_autonomie = total_self_consumed / total_cons if total_cons > 0 else 0.0
    surplus_kwh = max(0.0, total_prod - total_self_consumed)
    energie_achetee_kwh = max(0.0, total_cons - total_self_consumed)
    
    return {
        "taux_autoconsommation": taux_autoconsommation,
        "taux_autonomie": taux_autonomie,
        "taux_autosuffisance": taux_autonomie,
        "surplus_kwh": surplus_kwh,
        "energie_achetee_kwh": energie_achetee_kwh,
        "energie_autoconsommee_kwh": total_self_consumed
    }
