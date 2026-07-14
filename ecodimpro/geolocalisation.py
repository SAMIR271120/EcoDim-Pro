import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

def geocoder_adresse(adresse: str) -> dict:
    """
    Géocode une adresse en coordonnées de latitude et longitude en utilisant Nominatim (OpenStreetMap).
    Requiert un User-Agent unique respectant les conditions d'usage d'OSM.
    
    Retourne :
        dict : {"latitude": float, "longitude": float, "adresse_formatee": str}
        ou None si l'adresse n'est pas trouvée ou en cas d'erreur de service.
    """
    if not adresse or not adresse.strip():
        return None
        
    try:
        # Nominatim exige un user-agent unique pour identifier l'application
        geolocator = Nominatim(user_agent="ecodimpro_residential_solar_calculator_v1")
        
        # Timeout configuré à 5 secondes
        location = geolocator.geocode(adresse.strip(), timeout=5)
        
        if location:
            return {
                "latitude": float(location.latitude),
                "longitude": float(location.longitude),
                "adresse_formatee": str(location.address)
            }
        return None
        
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logging.error(f"Erreur de géocodage Nominatim (Réseau/Service) : {e}")
        return None
    except Exception as e:
        logging.error(f"Erreur inattendue lors du géocodage : {e}")
        return None
