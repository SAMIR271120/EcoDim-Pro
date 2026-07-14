import pytest
import pandas as pd
from ecodimpro.bilan import calc_autoconsommation
from ecodimpro.batterie import gain_autoconsommation_avec_batterie

def test_calc_autoconsommation_annuel():
    # Production = 3000 kWh, Consommation = 4000 kWh
    # Sans profil temporel, la fraction autoconsommée estimée est 35% de la production, soit 3000 * 0.35 = 1050 kWh
    res = calc_autoconsommation(3000.0, 4000.0)
    assert res["energie_autoconsommee_kwh"] == 1050.0
    assert res["taux_autoconsommation"] == 0.35
    assert res["taux_autonomie"] == 1050.0 / 4000.0
    assert res["surplus_kwh"] == 3000.0 - 1050.0
    assert res["energie_achetee_kwh"] == 4000.0 - 1050.0

    # Cas où la production est énorme : 10000 kWh, Consommation = 2000 kWh
    # 35% de 10000 = 3500 kWh, mais limité par la consommation (2000 kWh)
    res_enorme = calc_autoconsommation(10000.0, 2000.0)
    assert res_enorme["energie_autoconsommee_kwh"] == 2000.0
    assert res_enorme["taux_autoconsommation"] == 2000.0 / 10000.0
    assert res_enorme["taux_autonomie"] == 1.0
    assert res_enorme["surplus_kwh"] == 8000.0
    assert res_enorme["energie_achetee_kwh"] == 0.0

def test_calc_autoconsommation_temporel():
    # Profils temporels sur 3 heures
    prod = pd.Series([1.0, 2.0, 0.5])
    cons = pd.Series([1.5, 1.0, 1.0])
    # Heure 1 : min(1.0, 1.5) = 1.0
    # Heure 2 : min(2.0, 1.0) = 1.0
    # Heure 3 : min(0.5, 1.0) = 0.5
    # Total autoconsommé = 2.5 kWh
    # Total prod = 3.5 kWh
    # Total cons = 3.5 kWh
    res = calc_autoconsommation(prod, cons)
    assert res["energie_autoconsommee_kwh"] == 2.5
    assert res["taux_autoconsommation"] == 2.5 / 3.5
    assert res["taux_autonomie"] == 2.5 / 3.5
    assert res["surplus_kwh"] == 3.5 - 2.5
    assert res["energie_achetee_kwh"] == 3.5 - 2.5

def test_batterie_simulation_horaire():
    # Profils horaires sur 3 heures (simulés)
    prod = pd.Series([3.0, 0.0, 0.0, 0.0]) # Longueur 4
    cons = pd.Series([1.0, 1.0, 1.0, 1.0])
    # Capacite = 2 kWh, rendement = 1.0 (eta = 1.0)
    # Heure 0 : prod=3, cons=1 -> direct=1, surplus=2. Stored in battery = min(2 * 1.0, 2 - 0) = 2. soc = 2.
    # Heure 1 : prod=0, cons=1 -> direct=0, deficit=1. discharge = min(1, 2) = 1. soc = 1. gain = 1
    # Heure 2 : prod=0, cons=1 -> direct=0, deficit=1. discharge = min(1, 1) = 1. soc = 0. gain = 2
    # Heure 3 : prod=0, cons=1 -> direct=0, deficit=1. discharge = min(1, 0) = 0. soc = 0. gain = 2
    # Autoconsommation sans batterie = sum(min(prod, cons)) = 1 + 0 + 0 + 0 = 1.0 kWh
    # Autoconsommation avec batterie = 1 + 2 = 3.0 kWh
    # Gain = 2 kWh, gain% = 200%
    
    # Pour forcer la simulation horaire dans le module (qui a un seuil len > 100), 
    # nous pouvons créer des séries plus longues ou patcher le seuil dans notre test.
    # Créons simplement des séries de 120 heures.
    prod_long = pd.Series([3.0] * 30 + [0.0] * 90) # 30h de production à 3kW, 90h à 0
    cons_long = pd.Series([1.0] * 120)            # 120h de conso à 1kW
    # Sans batterie :
    # Heure 0-29 : direct = 1.0 (Somme = 30 kWh)
    # Heure 30-119 : direct = 0.0
    # Total sans = 30 kWh
    # Avec batterie (capacité 2kWh, rendement 1.0) :
    # Les 30 premières heures, chaque heure produit 3kW, consomme 1kW, surplus 2kW.
    # La batterie se charge à 2kWh dès la première heure, puis reste pleine.
    # Dès que la production s'arrête (heure 30), la batterie se vide de 1kWh à l'heure 30, et 1kWh à l'heure 31.
    # Puis elle reste vide.
    # Total déchargé = 2.0 kWh
    
    res = gain_autoconsommation_avec_batterie(
        production_horaire=prod_long,
        consommation_horaire=cons_long,
        capacite_kwh=2.0,
        rendement_charge_decharge=1.0
    )
    assert res["autoconsommation_sans_batterie"] == 30.0
    assert res["autoconsommation_avec_batterie"] == 32.0
    assert res["gain_kwh"] == 2.0
    assert res["gain_pourcentage"] == (2.0 / 30.0) * 100.0

def test_batterie_simulation_fallback():
    # Si on passe des floats (totaux annuels), le fallback s'active.
    # Prod = 3000, Cons = 4000, Batterie Cap = 5 kWh, Rendement = 0.9
    res = gain_autoconsommation_avec_batterie(3000.0, 4000.0, 5.0, 0.9)
    assert res["autoconsommation_sans_batterie"] > 0
    assert res["autoconsommation_avec_batterie"] > res["autoconsommation_sans_batterie"]
    assert res["gain_kwh"] > 0
    assert res["gain_pourcentage"] > 0
