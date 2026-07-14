import os
import pytest
from pathlib import Path
from ecodimpro.rapport import generer_rapport_pdf

def test_generer_rapport_pdf(tmp_path):
    output_pdf = tmp_path / "test_rapport_output.pdf"
    
    client_info = {
      "prenom": "Albert",
      "nom": "Martin",
      "adresse": "45 Avenue de la République, 69000 Lyon",
      "email": "contact.martin@email.com",
      "societe": "Martin SARL",
      "notes": "Notes test d'audit pour le logement de la famille Martin.",
      "installateur_nom": "EcoDim Expertises",
      "date": "2026-06-21",
      "nom_etude": "Moyen Foyer Lyon Solaire"
    }
    
    resultats = {
        "production_pv_annuelle": 3300.0,
        "production_pv_mensuelle": [100.0, 150.0, 250.0, 350.0, 400.0, 450.0, 450.0, 400.0, 300.0, 200.0, 150.0, 100.0],
        "besoin_ecs_kwh": 2000.0,
        "besoin_chauffage_kwh": 6000.0,
        "besoin_elec_kwh": 3500.0,
        "bilan_pv": {
            "taux_autoconsommation": 45.0,
            "taux_autosuffisance": 33.0,
            "surplus_injecte": 2145.0
        },
        "bilan_th": {
            "taux_couverture": 0.75,
            "production_thermique": 2000.0,
            "energie_appoint": 500.0
        },
        "vol_ballon": 300.0,
        "economies_annuelles": 850.0,
        "capex_total": 10200.0,
        "payback_simple": 12.0,
        "van": 2300.0,
        "pans_toiture": [
            {
                "nom": "Pan principal Sud",
                "type": "Toiture en pente",
                "surface_disponible_m2": 40.0,
                "surface_obstacles_m2": 2.0,
                "surface_utile_m2": 38.0,
                "orientation": "S",
                "azimut": 0.0,
                "inclinaison": 30,
                "ombrage_partiel": False
            }
        ],
        "equipements": {
            "panneau": {
                "id": "pv_std_425",
                "nom": "Vertex S+ 425Wc",
                "puissance_wc": 425,
                "surface_m2": 1.95,
                "longueur_m": 1.72,
                "largeur_m": 1.13,
                "rendement_pct": 21.8,
                "garantie_produit_ans": 15,
                "garantie_production_ans": 25,
                "prix_unitaire_eur": 220
            },
            "onduleur": {
                "id": "ond_string_3kw",
                "nom": "Fronius Primo 3.0-1",
                "puissance_kw": 3.0,
                "type": "string",
                "rendement_pct": 98.0,
                "garantie_ans": 5,
                "prix_eur": 1200
            },
            "batterie": {
                "id": "bat_lfp_5",
                "nom": "BYD Battery-Box Premium 5.1",
                "capacite_kwh": 5.12,
                "technologie": "LFP",
                "rendement_pct": 95,
                "garantie_ans": 10,
                "cycles_garantis": 6000,
                "prix_eur": 3800
            },
            "nb_panneaux": 10
        },
        "cablage": {
            "section_dc_mm2": 4.0,
            "cable_dc_m": 45.0,
            "cable_ac_m": 5.0,
            "cable_terre_m": 25.0
        },
        "capex_details": {
            "panneaux_fact": 2200.0,
            "onduleur_fact": 1200.0,
            "pose_fact": 2500.0,
            "thermique_fact": 2800.0,
            "batterie_fact": 3800.0
        },
        "dimensionnement": {
            "surface_m2": 100.0,
            "duree_financement": 20,
            "taux_act": 0.03,
            "prix_reseau": 0.2516,
            "tarif_rachat": 0.13,
            "umur": 1.5,
            "uph": 0.3,
            "upb": 0.45,
            "dh14": 2000.0,
            "capacite_bat": 5.12,
            "rendement_bat": 0.95,
            "reseau_type": "230V monophasé",
            "cos_phi": 0.95,
            "injection_limite_active": False,
            "injection_limite_kw": 3.0
        },
        "station_meteo": "PVGIS-SARAH2-Lyon",
        "disclaimer_dpe": "Estimation indicative 3CL-DPE. Ce document ne remplace pas un diagnostic officiel."
    }
    
    pdf_path = generer_rapport_pdf(resultats, client_info, logo_path=None, output_path=str(output_pdf))
    
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0
