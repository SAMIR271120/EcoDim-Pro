import pytest
import pandas as pd
from unittest.mock import patch
import requests
from ecodimpro.pv import detecter_zone_climatique, recuperer_irradiation_pvgis, production_pv_mensuelle, production_pv_annuelle

def test_detecter_zone_climatique():
    # Paris (48.85, 2.35) -> H1
    assert detecter_zone_climatique(48.85, 2.35) == "H1"
    # Brest (48.39, -4.48) -> H2 (Lat > 46.5, Lon <= 2.0)
    assert detecter_zone_climatique(48.39, -4.48) == "H2"
    # Lyon (45.76, 4.83) -> H2 (Lat between 44.5 and 46.5)
    assert detecter_zone_climatique(45.76, 4.83) == "H2"
    # Nice (43.70, 7.26) -> H3 (Lat <= 44.5)
    assert detecter_zone_climatique(43.70, 7.26) == "H3"

@patch("requests.get")
def test_recuperer_irradiation_pvgis_fallback(mock_get):
    # Simulate a network timeout to force the fallback
    mock_get.side_effect = requests.RequestException("Timeout")
    
    # We call with Nice coordinates (H3)
    data = recuperer_irradiation_pvgis(43.70, 7.26, 30, 0)
    
    assert data["meta"]["source"] == "fallback"
    assert data["meta"]["zone_climatique"] == "H3"
    assert len(data["outputs"]["monthly"]) == 12
    # Check that January has a value matching H3 fallback (H3 Jan = 60.0, E_m = 60.0 * 0.86 = 51.6)
    jan_data = data["outputs"]["monthly"][0]
    assert jan_data["month"] == 1
    assert pytest.approx(jan_data["E_m"], 0.01) == 60.0 * 0.86

@patch("requests.get")
def test_production_pv_mensuelle_scaling(mock_get):
    # Simulate network error to use H3 fallback values
    mock_get.side_effect = requests.RequestException("Timeout")
    
    # Call production for 3 kWp and PR = 0.80
    # H3 Jan fallback is 60.0 * 0.86
    # So expected Jan prod is: (60.0 * 0.86) * 3 * (0.80 / 0.86) = 60.0 * 3 * 0.80 = 144 kWh
    res = production_pv_mensuelle(43.70, 7.26, kwp=3.0, inclinaison=30, azimut=0, performance_ratio=0.80)
    
    assert isinstance(res, pd.Series)
    assert len(res) == 12
    assert pytest.approx(res[1], 0.01) == 144.0

def test_production_pv_annuelle():
    # If we run with fallback (which we patch or let happen if offline)
    # Nice (H3): sum of H3 fallback = 1630. For 3 kWp and 0.80 PR, annual should be 1630 * 3 * 0.8 = 3912 kWh
    with patch("requests.get", side_effect=requests.RequestException("Timeout")):
        annual = production_pv_annuelle(43.70, 7.26, kwp=3.0, performance_ratio=0.80)
        assert pytest.approx(annual, 0.01) == 1630 * 3 * 0.80
