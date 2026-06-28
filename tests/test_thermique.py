import pytest
from ecodimpro.thermique import dimensionner_ballon, surface_capteurs_recommandee, couverture_ecs

def test_dimensionner_ballon():
    assert dimensionner_ballon(200.0) == 300.0
    assert dimensionner_ballon(0.0) == 0.0
    assert dimensionner_ballon(-10.0) == 0.0

def test_surface_capteurs_recommandee():
    # H1/H2 should return 1.75 m2 per person
    assert surface_capteurs_recommandee(4, "H1") == 7.0
    assert surface_capteurs_recommandee(4, "H2") == 7.0
    # H3 should return 1.25 m2 per person
    assert surface_capteurs_recommandee(4, "H3") == 5.0
    # Unknown zone should default to H2
    assert surface_capteurs_recommandee(4, "XYZ") == 7.0
    # 0 people
    assert surface_capteurs_recommandee(0, "H1") == 0.0

def test_couverture_ecs():
    # Scenario: surface=4m2, rendement=0.5, besoin_ecs=2000 kWh/an, irradiation=1200 kWh/m2/an
    # production = 4 * 0.5 * 1200 = 2400 kWh/an
    # raw_coverage = 2400 / 2000 = 1.2 (120%)
    # This should be capped at 80% (0.80) for useful solar energy.
    # It should also trigger a warning because raw_coverage (120%) > 85%.
    res = couverture_ecs(
        surface_capteurs=4.0,
        rendement_capteur=0.5,
        besoin_ecs_kwh=2000.0,
        irradiation_annuelle_kwh_m2=1200.0
    )
    assert res["production_thermique"] == 2400.0
    assert res["taux_couverture"] == 0.80
    assert res["energie_appoint"] == 2000.0 * 0.20
    assert "Attention" in res["warning"]
    
    # Scenario: under-dimensioned system
    # production = 1 * 0.5 * 1000 = 500 kWh/an
    # raw_coverage = 500 / 2000 = 0.25 (25%)
    # This should not trigger warning, and coverage should be 0.25
    res_under = couverture_ecs(
        surface_capteurs=1.0,
        rendement_capteur=0.5,
        besoin_ecs_kwh=2000.0,
        irradiation_annuelle_kwh_m2=1000.0
    )
    assert res_under["production_thermique"] == 500.0
    assert res_under["taux_couverture"] == 0.25
    assert res_under["energie_appoint"] == 1500.0
    assert res_under["warning"] == ""
