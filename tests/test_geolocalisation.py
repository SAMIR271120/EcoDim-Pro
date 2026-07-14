import pytest
from unittest.mock import patch, MagicMock
from geopy.exc import GeocoderTimedOut
from ecodimpro.geolocalisation import geocoder_adresse

@patch("geopy.geocoders.Nominatim.geocode")
def test_geocoder_adresse_succes(mock_geocode):
    # Mock du résultat de geocode
    mock_location = MagicMock()
    mock_location.latitude = 48.7824
    mock_location.longitude = 2.4472
    mock_location.address = "Créteil, Val-de-Marne, Île-de-France, France"
    mock_geocode.return_value = mock_location
    
    res = geocoder_adresse("Créteil")
    
    assert res is not None
    assert res["latitude"] == 48.7824
    assert res["longitude"] == 2.4472
    assert "Créteil" in res["adresse_formatee"]
    
    # Vérification que geocode a été appelé
    mock_geocode.assert_called_once_with("Créteil", timeout=5)

@patch("geopy.geocoders.Nominatim.geocode")
def test_geocoder_adresse_non_trouve(mock_geocode):
    # Mock pour adresse inconnue (retourne None)
    mock_geocode.return_value = None
    
    res = geocoder_adresse("AdresseInexistanteDansLeMonde12345")
    
    assert res is None

@patch("geopy.geocoders.Nominatim.geocode")
def test_geocoder_adresse_timeout(mock_geocode):
    # Mock pour erreur de timeout
    mock_geocode.side_effect = GeocoderTimedOut("Timeout Nominatim")
    
    res = geocoder_adresse("Paris")
    
    assert res is None

def test_geocoder_adresse_vide():
    # Entrée vide
    assert geocoder_adresse("") is None
    assert geocoder_adresse("   ") is None
    assert geocoder_adresse(None) is None
