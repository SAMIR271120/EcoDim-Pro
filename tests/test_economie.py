import pytest
from ecodimpro.economie import calc_capex_pv, calc_capex_thermique, economies_annuelles, payback_simple, van

def test_capex():
    assert calc_capex_pv(3.0, 1900.0) == 5700.0
    assert calc_capex_thermique(4.0, 700.0) == 2800.0
    assert calc_capex_pv(-1) == 0.0

def test_economies_annuelles():
    # autoconso=1500 kWh, price=0.25, surplus=500 kWh, rachat=0.10
    # Expected: 1500 * 0.25 + 500 * 0.10 = 375 + 50 = 425
    assert economies_annuelles(1500.0, 0.25, 500.0, 0.10) == 425.0
    # Zero or negative inputs
    assert economies_annuelles(0.0, 0.25) == 0.0
    assert economies_annuelles(-10, 0.25) == 0.0

def test_payback_simple():
    # CAPEX=5000, annual economies=500 -> 10 years
    assert payback_simple(5000.0, 500.0) == 10.0
    # Zero economies should return infinity
    assert payback_simple(5000.0, 0.0) == float("inf")
    assert payback_simple(5000.0, -100.0) == float("inf")

def test_van():
    # CAPEX=1000, economies=200, duration=2, rate=0.05
    # Year 1 CF = 200 / 1.05 = 190.476
    # Year 2 CF = 200 / 1.1025 = 181.405
    # Total CF = 371.881
    # NPV = 371.881 - 1000 = -628.118
    expected = (200.0 / 1.05) + (200.0 / 1.1025) - 1000.0
    result = van(capex_total=1000.0, economies_annuelles=200.0, duree_ans=2, taux_actualisation=0.05)
    assert pytest.approx(result, 0.01) == expected
