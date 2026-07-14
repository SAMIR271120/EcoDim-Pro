import math
import pandas as pd
from typing import Union

def gain_autoconsommation_avec_batterie(
    production_horaire: Union[pd.Series, list, float],
    consommation_horaire: Union[pd.Series, list, float],
    capacite_kwh: float,
    rendement_charge_decharge: float = 0.9
) -> dict:
    """
    Simule l'impact d'une batterie de stockage sur le taux d'autoconsommation.
    
    Si les profils sont des séries temporelles (ex: 8760 heures) :
        Effectue une simulation chronologique heure par heure de l'état de charge (SOC)
        de la batterie.
    Si les profils ne sont pas disponibles sous forme horaire (ex: totaux annuels ou mensuels) :
        Utilise une méthode empirique simplifiée mensuelle basée sur le nombre de cycles
        moyens d'une batterie résidentielle (estimé à 25 cycles complets par mois).
        
    Retourne un dictionnaire avec :
        - 'autoconsommation_sans_batterie': kWh consommés directement du PV
        - 'autoconsommation_avec_batterie': kWh consommés du PV + via la batterie
        - 'gain_kwh': électricité supplémentaire autoconsommée grâce à la batterie
        - 'gain_pourcentage': augmentation relative de l'autoconsommation
    """
    capacite = max(0.0, capacite_kwh)
    
    # 1. Cas Simulation Horaire (Profils temporels fournis de longueur > 100)
    if (isinstance(production_horaire, pd.Series) and isinstance(consommation_horaire, pd.Series) 
            and len(production_horaire) > 100):
        
        # Racine carrée pour répartir les pertes équitablement entre charge et décharge
        eta = math.sqrt(max(0.0, min(1.0, rendement_charge_decharge)))
        
        soc = 0.0
        total_direct_autoconso = 0.0
        total_discharged = 0.0
        
        for prod, cons in zip(production_horaire, consommation_horaire):
            if prod >= cons:
                # La production couvre la consommation en direct
                direct = cons
                total_direct_autoconso += direct
                
                # Le surplus va charger la batterie
                surplus = prod - cons
                charge_stored = min(surplus * eta, capacite - soc)
                soc += charge_stored
            else:
                # La production ne couvre pas toute la consommation
                direct = prod
                total_direct_autoconso += direct
                
                # Le déficit est comblé par la batterie
                deficit = cons - prod
                discharge_from_soc = min(deficit / eta, soc)
                soc -= discharge_from_soc
                
                # Énergie utile restituée à la charge
                discharged_used = discharge_from_soc * eta
                total_discharged += discharged_used
                
        auto_sans = total_direct_autoconso
        auto_avec = total_direct_autoconso + total_discharged
        gain = total_discharged
        
    # 2. Cas Modèle Mensuel ou Annuel Simplifié (Fallback)
    else:
        # Si ce sont des valeurs annuelles globales, on les divise en 12 mois fictifs
        if not isinstance(production_horaire, pd.Series):
            prod_val = float(production_horaire)
            cons_val = float(consommation_horaire)
            
            # Répartition mensuelle fictive standard
            weights = [0.03, 0.05, 0.08, 0.11, 0.13, 0.14, 0.15, 0.13, 0.10, 0.07, 0.04, 0.03]
            prod_m = pd.Series([prod_val * w for w in weights])
            cons_m = pd.Series([cons_val / 12.0] * 12)
        else:
            prod_m = production_horaire
            if not isinstance(consommation_horaire, pd.Series):
                cons_val = float(consommation_horaire)
                cons_m = pd.Series([cons_val / len(prod_m)] * len(prod_m), index=prod_m.index)
            else:
                cons_m = consommation_horaire
            
        auto_sans_total = 0.0
        auto_avec_total = 0.0
        
        # Pour chaque mois, on estime la charge/décharge de la batterie
        # On suppose ~25 cycles complets par mois en moyenne (0.8 cycle/jour)
        cycles_par_mois = 25.0
        throughput_max_mensuel = capacite * cycles_par_mois * rendement_charge_decharge
        
        for p, c in zip(prod_m, cons_m):
            # Autoconsommation de base du mois sans stockage (environ 35% de la production PV, plafonné par conso)
            auto_sans_m = min(p * 0.35, c)
            auto_sans_total += auto_sans_m
            
            # Énergie potentiellement stockable
            surplus_m = max(0.0, p - auto_sans_m)
            # Énergie requise pour combler le déficit
            deficit_m = max(0.0, c - auto_sans_m)
            
            # Gain mensuel limité par le surplus, le déficit, et le débit max de la batterie
            gain_m = min(surplus_m * rendement_charge_decharge, deficit_m, throughput_max_mensuel)
            
            auto_avec_total += auto_sans_m + gain_m
            
        auto_sans = auto_sans_total
        auto_avec = auto_avec_total
        gain = auto_avec - auto_sans
        
    gain_pourcentage = (gain / auto_sans * 100.0) if auto_sans > 0.0 else 0.0
    
    return {
        "autoconsommation_sans_batterie": auto_sans,
        "autoconsommation_avec_batterie": auto_avec,
        "gain_kwh": gain,
        "gain_pourcentage": gain_pourcentage
    }
