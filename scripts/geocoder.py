import time
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

logger = logging.getLogger(__name__)

_cache: dict = {}
_geolocator = Nominatim(user_agent="wildlife-news-map-india")

INDIA_BOUNDS = {'lat_min': 6, 'lat_max': 37, 'lon_min': 68, 'lon_max': 98}


def geocode(place_name: str):
    """Returns (lat, lon) or None. Caches results within the process."""
    if place_name in _cache:
        return _cache[place_name]

    query = f"{place_name}, India"
    try:
        time.sleep(1)
        location = _geolocator.geocode(query, timeout=10)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning(f"Geocoding failed for '{place_name}': {e}")
        _cache[place_name] = None
        return None

    if location is None:
        logger.debug(f"No result for '{place_name}'")
        _cache[place_name] = None
        return None

    lat, lon = location.latitude, location.longitude
    b = INDIA_BOUNDS
    if not (b['lat_min'] <= lat <= b['lat_max'] and b['lon_min'] <= lon <= b['lon_max']):
        logger.warning(f"'{place_name}' geocoded outside India bounds: ({lat}, {lon})")
        _cache[place_name] = None
        return None

    result = (round(lat, 6), round(lon, 6))
    _cache[place_name] = result
    return result
