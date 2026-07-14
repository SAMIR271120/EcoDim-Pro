"""
tests/test_technique.py — Tests unitaires de validation pour le dimensionnement technique.
"""
import pytest
import os
import json
import pandas as pd
from ecodimpro.cablage import estimer_section_cable, estimer_metrage_cablage
from ecodimpro.equipements import charger_catalogue, filtrer_panneaux_par_surface
from ecodimpro.pv import calculer_nb_panneaux_max, puissance_totale_kwc


def test_cablage_section():
    # Test avec des valeurs typiques
    # I = 12A, L = 15m, U = 400V, Chute max = 3%
    section = estimer_section_cable(12.0, 15.0, 3.0, 400.0)
    assert section in [1.5, 2.5, 4.0, 6.0, 10.0, 16.0]
    
    # Avec une grande longueur, la section doit augmenter pour limiter la chute de tension
    section_long = estimer_section_cable(12.0, 120.0, 3.0, 400.0)
    assert section_long > section


def test_cablage_metrage():
    metrages = estimer_metrage_cablage(nb_panneaux=10, distance_toit_onduleur_m=15.0)
    # L_dc = 15 * 2 + 10 * 1.5 = 30 + 15 = 45 m
    assert metrages["cable_dc_m"] == 45.0
    # L_ac = 5.0 m (fixe)
    assert metrages["cable_ac_m"] == 5.0
    # L_terre = 15 + 10 = 25 m
    assert metrages["cable_terre_m"] == 25.0


def test_equipements_catalogue():
    panneaux = charger_catalogue("panneaux")
    assert len(panneaux) > 0
    assert "id" in panneaux[0]
    assert "puissance_wc" in panneaux[0]
    assert "surface_m2" in panneaux[0]

    onduleurs = charger_catalogue("onduleurs")
    assert len(onduleurs) > 0

    batteries = charger_catalogue("batteries")
    assert len(batteries) > 0


def test_estimation_nb_panneaux():
    panneau_test = {
        "id": "pv_std_425",
        "nom": "Panneau Test",
        "puissance_wc": 425,
        "surface_m2": 1.95,
        "prix_unitaire_eur": 220
    }
    # Surface utile = 30 m2, foisonnement = 0.85
    # nb_max = floor(30 * 0.85 / 1.95) = floor(25.5 / 1.95) = floor(13.07) = 13
    nb_max = calculer_nb_panneaux_max(30.0, panneau_test, 0.85)
    assert nb_max == 13

    # Puissance crête = 13 * 425 / 1000 = 5.525 kWc
    p_kwc = puissance_totale_kwc(nb_max, panneau_test)
    assert p_kwc == 5.525


def test_filtrer_panneaux():
    # Tester le filtrage par surface utile
    panneaux = charger_catalogue("panneaux")
    p_compatibles = filtrer_panneaux_par_surface(panneaux, 30.0)
    assert len(p_compatibles) > 0
