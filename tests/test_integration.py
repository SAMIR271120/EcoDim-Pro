import json
import pytest
from pathlib import Path
from unittest.mock import patch
import requests

from ecodimpro.besoins import calc_besoin_elec, calc_besoin_ecs, calc_besoin_chauffage_legacy as calc_besoin_chauffage
from ecodimpro.pv import production_pv_annuelle, recuperer_irradiation_pvgis
from ecodimpro.thermique import couverture_ecs, surface_capteurs_recommandee
from ecodimpro.batterie import gain_autoconsommation_avec_batterie
from ecodimpro.bilan import calc_autoconsommation
from ecodimpro.economie import calc_capex_pv, calc_capex_thermique, economies_annuelles, payback_simple, van

CAS_DIR = Path("tests/cas_exemples")

@pytest.mark.parametrize("cas_filename", ["petit_foyer.json", "moyen_foyer.json", "grand_foyer.json"])
@patch("requests.get")
def test_integration_foyer(mock_get, cas_filename):
    # Simulate network error to use local climate fallback for repeatability
    mock_get.side_effect = requests.RequestException("Timeout")
    
    filepath = CAS_DIR / cas_filename
    assert filepath.exists()
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # 1. Besoins énergétiques
    besoin_elec = calc_besoin_elec(data["besoins_elec"]["appareils"])
    assert besoin_elec > 0.0
    
    nb_p = data["besoins_ecs"]["nb_personnes"]
    litres_p = data["besoins_ecs"]["litres_par_jour_par_personne"]
    t_ent = data["besoins_ecs"]["t_entree"]
    t_sort = data["besoins_ecs"]["t_sortie"]
    besoin_ecs = calc_besoin_ecs(nb_p, litres_p, t_ent, t_sort)
    if nb_p > 0:
        assert besoin_ecs > 0.0
    else:
        assert besoin_ecs == 0.0
        
    surf = data["logement"]["surface_m2"]
    isol = data["logement"]["niveau_isolation"]
    dju = data["logement"]["deg_jours_unifies"]
    t_cons = data["logement"]["t_consigne"]
    zone = data["logement"]["zone_climatique"]
    besoin_chauffage = calc_besoin_chauffage(surf, isol, dju, t_cons, zone)
    assert besoin_chauffage > 0.0
    
    # 2. PV Production
    kwp = data["solaire_pv"]["kwp"]
    inc = data["solaire_pv"]["inclinaison"]
    azi = data["solaire_pv"]["azimut"]
    pr = data["solaire_pv"]["performance_ratio"]
    
    # For simulation, we detect coordinates based on typical French locations
    # (let's assume lat=45.0, lon=2.0 which is in France H2 zone)
    lat, lon = 45.0, 2.0
    if zone == "H3":
        lat, lon = 43.5, 3.8 # Montpellier H3
    elif zone == "H1":
        lat, lon = 48.8, 2.3 # Paris H1
        
    prod_pv_an = production_pv_annuelle(lat, lon, kwp, inc, azi, pr)
    assert prod_pv_an > 0.0
    
    # 3. Solaire thermique
    surf_th = data["solaire_thermique"]["surface_capteurs"]
    rend_th = data["solaire_thermique"]["rendement_capteur"]
    
    # Get annual irradiation from PVGIS data (or fallback)
    pvgis_data = recuperer_irradiation_pvgis(lat, lon, inc, azi)
    # Sum of H(i)_d * days_in_month
    irrad_annuelle = 0.0
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for m_data in pvgis_data["outputs"]["monthly"]:
        m = m_data["month"]
        irrad_annuelle += m_data["H(i)_d"] * days_in_month[m]
        
    bilan_th = couverture_ecs(surf_th, rend_th, besoin_ecs, irrad_annuelle)
    assert "production_thermique" in bilan_th
    assert "taux_couverture" in bilan_th
    assert "energie_appoint" in bilan_th
    
    # 4. Batterie & Autoconsommation
    cap_bat = data["batterie"]["capacite_kwh"]
    rend_bat = data["batterie"]["rendement_charge_decharge"]
    
    if cap_bat > 0:
        bilan_bat = gain_autoconsommation_avec_batterie(prod_pv_an, besoin_elec, cap_bat, rend_bat)
        auto_kwh = bilan_bat["autoconsommation_avec_batterie"]
        gain_kwh = bilan_bat["gain_kwh"]
        assert auto_kwh > 0.0
        assert gain_kwh > 0.0
    else:
        bilan_pv = calc_autoconsommation(prod_pv_an, besoin_elec)
        auto_kwh = bilan_pv["energie_autoconsommee_kwh"]
        gain_kwh = 0.0
        assert auto_kwh > 0.0
        
    # surplus injecté
    surplus_injecte = max(0.0, prod_pv_an - auto_kwh)
    
    # 5. Rentabilité économique
    prix_elec = data["economie"]["prix_elec_eur_kwh"]
    prix_rachat = data["economie"]["tarif_rachat_eur_kwh"]
    prix_kwp = data["economie"]["prix_eur_par_kwp"]
    prix_m2 = data["economie"]["prix_eur_par_m2"]
    
    capex_pv = calc_capex_pv(kwp, prix_kwp)
    capex_th = calc_capex_thermique(surf_th, prix_m2)
    # Ajouter le coût de la batterie si présente (mettons 600 €/kWh)
    capex_bat = cap_bat * 600.0
    capex_total = capex_pv + capex_th + capex_bat
    
    # Économies annuelles sur l'électricité + surplus + appoint d'eau chaude évité par le thermique (si applicable)
    # Économies d'électricité = auto_kwh * prix_elec
    # Vente du surplus = surplus_injecte * prix_rachat
    # Économie ECS thermique = (besoin_ecs * taux_couverture) * prix_elec (si appoint est électrique par exemple)
    taux_couv_th = bilan_th["taux_couverture"]
    economie_ecs_val = (besoin_ecs * taux_couv_th) * prix_elec
    
    economies = economies_annuelles(auto_kwh, prix_elec, surplus_injecte, prix_rachat) + economie_ecs_val
    assert economies >= 0.0
    
    payback = payback_simple(capex_total, economies)
    van_val = van(capex_total, economies, duree_ans=20, taux_actualisation=0.03)
    
    assert payback >= 0.0
    assert isinstance(van_val, float)
