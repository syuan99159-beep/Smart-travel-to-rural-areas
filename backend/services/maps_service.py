import os
import math
import logging
import requests
from urllib.parse import urlencode

from dotenv import load_dotenv

from models.cache_model import get_travel_cache, save_travel_cache


load_dotenv()


logger = logging.getLogger(__name__)


def _as_location(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return {"name": text, "address": text}
    return value


def _get_area(value):
    value = _as_location(value)
    if not value:
        return ""
    return (value.get("area") or value.get("region") or "").strip()


def _get_location_text(value):
    value = _as_location(value)
    if not value:
        return ""
    return (value.get("address") or value.get("area") or value.get("region") or value.get("name") or "").strip()


def _get_address_text(value):
    value = _as_location(value)
    if not value:
        return ""
    return (value.get("address") or "").strip()


def _normalize_text(value):
    return (value or "").strip().lower()


def _same_place_signature(value):
    value = _as_location(value)
    if not value:
        return None
    address = _get_address_text(value)
    if address:
        return f"address:{_normalize_text(address)}"
    name = _normalize_text(value.get("name"))
    area = _normalize_text(value.get("area") or value.get("region"))
    if name or area:
        return f"name_area:{name}|{area}"
    return None


def _is_same_place(origin, destination):
    origin = _as_location(origin)
    destination = _as_location(destination)
    origin_latlng = _extract_latlng(origin)
    dest_latlng = _extract_latlng(destination)
    if origin_latlng and dest_latlng and origin_latlng == dest_latlng:
        return origin_latlng == dest_latlng

    origin_address = _get_address_text(origin)
    dest_address = _get_address_text(destination)
    if origin_address and dest_address:
        return _normalize_text(origin_address) == _normalize_text(dest_address)

    if not origin_address and not dest_address and not origin_latlng and not dest_latlng:
        origin_signature = _same_place_signature(origin)
        dest_signature = _same_place_signature(destination)
        return bool(origin_signature and origin_signature == dest_signature)

    return False


def _has_coordinates(value):
    return value and ("lat" in value or "latitude" in value) and ("lng" in value or "longitude" in value)


def _extract_latlng(value):
    value = _as_location(value)
    if not value:
        return None
    lat = value.get("lat") or value.get("latitude")
    lng = value.get("lng") or value.get("longitude")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except Exception:
        return None


def build_location_key(location):
    location = _as_location(location)
    if not location:
        return ""
    latlng = _extract_latlng(location)
    if latlng:
        return f"lat:{latlng[0]:.6f},lng:{latlng[1]:.6f}"
    name = location.get("name") or ""
    address = location.get("address") or ""
    return f"name:{name.strip()}|addr:{address.strip()}"


def should_use_cache(origin_key, destination_key):
    # Always attempt cache first
    return True


def get_travel_cache_record(origin_key, destination_key):
    return get_travel_cache(origin_key, destination_key)


def save_travel_cache_record(origin_key, destination_key, travel_minutes, distance_text, duration_text, source):
    save_travel_cache(origin_key, destination_key, travel_minutes, distance_text, duration_text, source)


def get_fake_travel_time(origin, destination):
    origin = _as_location(origin)
    destination = _as_location(destination)
    # preserve original fallback behavior but return dict
    if origin is None or destination is None:
        return {"travel_minutes": 30, "distance_text": None, "duration_text": "30 分鐘", "source": "fallback_maps", "warning": None}

    latlng_a = _extract_latlng(origin)
    latlng_b = _extract_latlng(destination)

    if latlng_a and latlng_b:
        radius = 6371.0
        lat1, lng1 = latlng_a
        lat2, lng2 = latlng_b
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = radius * c
        minutes = max(8, int(round(distance_km / 25 * 60 + 8)))
        return {"travel_minutes": minutes, "distance_text": f"{round(distance_km,2)} km", "duration_text": f"{minutes} 分鐘", "source": "fallback_maps", "warning": None}

    origin_area = _get_area(origin)
    destination_area = _get_area(destination)

    if not origin_area:
        return {"travel_minutes": 30, "distance_text": None, "duration_text": "30 分鐘", "source": "fallback_maps", "warning": None}

    if origin_area == destination_area:
        return {"travel_minutes": 10, "distance_text": None, "duration_text": "10 分鐘", "source": "fallback_maps", "warning": None}

    return {"travel_minutes": 25, "distance_text": None, "duration_text": "25 分鐘", "source": "fallback_maps", "warning": None}


def _call_google_directions(origin, destination, api_key):
    origin = _as_location(origin)
    destination = _as_location(destination)
    # Build origin/destination strings prefer lat,lng
    origin_latlng = _extract_latlng(origin)
    dest_latlng = _extract_latlng(destination)

    if origin_latlng:
        origin_param = f"{origin_latlng[0]},{origin_latlng[1]}"
    else:
        origin_param = _get_location_text(origin)

    if dest_latlng:
        dest_param = f"{dest_latlng[0]},{dest_latlng[1]}"
    else:
        dest_param = _get_location_text(destination)

    params = {
        "origin": origin_param,
        "destination": dest_param,
        "mode": "driving",
        "key": api_key,
    }
    url = f"https://maps.googleapis.com/maps/api/directions/json?{urlencode(params)}"
    logger.info("[maps] calling Google Directions API")
    logger.info("[maps] origin = %s", origin)
    logger.info("[maps] destination = %s", destination)
    logger.info("[maps] endpoint = %s", "https://maps.googleapis.com/maps/api/directions/json")
    logger.info("[maps] params = %s", {"origin": origin_param, "destination": dest_param, "mode": "driving", "key": "<redacted>" if api_key else None})
    resp = requests.get(url, timeout=8)
    logger.info("[maps] HTTP status = %s", resp.status_code)
    logger.debug("[maps] response = %s", resp.text[:1000])
    return resp


def get_google_travel_time(origin, destination):
    origin = _as_location(origin)
    destination = _as_location(destination)
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"success": False, "error": "missing_api_key"}

    try:
        resp = _call_google_directions(origin, destination, api_key)
    except Exception as e:
        logger.exception("[maps] Google Directions request failed")
        return {"success": False, "error": "request_failed", "exception": str(e)}

    if resp.status_code != 200:
        logger.warning("[maps] Google Directions HTTP %s: %s", resp.status_code, resp.text[:300])
        return {"success": False, "error": f"http_error_{resp.status_code}", "status_code": resp.status_code, "raw": resp.text, "warning": None}

    data = resp.json()
    logger.info("[maps] Google status = %s", data.get("status"))
    logger.info("[maps] error_message = %s", data.get("error_message"))
    status = data.get("status")
    if status != "OK":
        error_message = data.get("error_message")
        logger.warning("[maps] Google Directions status=%s error_message=%s", status, error_message)
        return {"success": False, "error": status, "raw": data, "warning": None}

    # parse legs[0]
    routes = data.get("routes") or []
    if not routes:
        return {"success": False, "error": "no_routes", "raw": data}

    legs = routes[0].get("legs") or []
    if not legs:
        return {"success": False, "error": "no_legs", "raw": data}

    leg = legs[0]
    duration = leg.get("duration") or {}
    distance = leg.get("distance") or {}
    travel_minutes = int(round((duration.get("value") or 0) / 60.0))
    distance_text = distance.get("text")
    duration_text = duration.get("text")

    return {
        "success": True,
        "travel_minutes": travel_minutes,
        "distance_text": distance_text,
        "duration_text": duration_text,
        "source": "google_maps",
    }


def get_travel_time(origin, destination):
    origin = _as_location(origin)
    destination = _as_location(destination)
    if _is_same_place(origin, destination):
        return {
            "travel_minutes": 0,
            "distance_text": "0",
            "duration_text": "0 分鐘",
            "source": "same_place",
            "warning": "同一地點內活動，無需移動",
        }

    # Build keys
    origin_key = build_location_key(origin)
    destination_key = build_location_key(destination)

    # Try cache
    if should_use_cache(origin_key, destination_key):
        cached = get_travel_cache_record(origin_key, destination_key)
        if cached:
            cached_source = cached.get("source") or "cache"
            cached_warning = None
            if cached_source == "fallback_maps":
                cached_warning = "目前使用系統估算車程"
            return {
                "travel_minutes": int(cached.get("travel_minutes") or 0),
                "distance_text": cached.get("distance_text"),
                "duration_text": cached.get("duration_text"),
                "source": cached_source,
                "warning": cached_warning,
            }

    use_real = os.environ.get("USE_REAL_MAPS", str(False)).lower() in ("1", "true", "yes")
    if use_real:
        google_result = get_google_travel_time(origin, destination)
        if google_result.get("success"):
            travel_minutes = google_result.get("travel_minutes")
            distance_text = google_result.get("distance_text")
            duration_text = google_result.get("duration_text")
            save_travel_cache_record(origin_key, destination_key, travel_minutes, distance_text, duration_text, "google_maps")
            return {"travel_minutes": travel_minutes, "distance_text": distance_text, "duration_text": duration_text, "source": "google_maps", "warning": None}
        else:
            logger.warning("[maps] Google Maps lookup failed: %s", google_result.get("error"))
            # On failure, fallback to fake but include warning
            fake = get_fake_travel_time(origin, destination)
            save_travel_cache_record(origin_key, destination_key, fake["travel_minutes"], fake.get("distance_text"), fake.get("duration_text"), "fallback_maps")
            return {"travel_minutes": fake["travel_minutes"], "distance_text": fake.get("distance_text"), "duration_text": fake.get("duration_text"), "source": "fallback_maps", "warning": "目前使用系統估算車程"}

    # real disabled, return fake
    fake = get_fake_travel_time(origin, destination)
    # do not save fake to cache unless desired; here we save to cache to speed repeat
    save_travel_cache_record(origin_key, destination_key, fake["travel_minutes"], fake.get("distance_text"), fake.get("duration_text"), "fallback_maps")
    return {"travel_minutes": fake["travel_minutes"], "distance_text": fake.get("distance_text"), "duration_text": fake.get("duration_text"), "source": "fallback_maps", "warning": "目前使用系統估算車程"}

