import os
import math
import requests
from urllib.parse import urlencode

from dotenv import load_dotenv

from models.cache_model import get_travel_cache, save_travel_cache


load_dotenv()


def _get_area(value):
    if not value:
        return ""
    return (value.get("area") or value.get("region") or "").strip()


def _has_coordinates(value):
    return value and ("lat" in value or "latitude" in value) and ("lng" in value or "longitude" in value)


def _extract_latlng(value):
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
    # preserve original fallback behavior but return dict
    if origin is None or destination is None:
        return {"travel_minutes": 30, "distance_text": None, "duration_text": "30 分鐘", "source": "fake", "warning": None}

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
        return {"travel_minutes": minutes, "distance_text": f"{round(distance_km,2)} km", "duration_text": f"{minutes} 分鐘", "source": "fake", "warning": None}

    origin_area = _get_area(origin)
    destination_area = _get_area(destination)

    if not origin_area:
        return {"travel_minutes": 30, "distance_text": None, "duration_text": "30 分鐘", "source": "fake", "warning": None}

    if origin_area == destination_area:
        return {"travel_minutes": 10, "distance_text": None, "duration_text": "10 分鐘", "source": "fake", "warning": None}

    return {"travel_minutes": 25, "distance_text": None, "duration_text": "25 分鐘", "source": "fake", "warning": None}


def _call_google_directions(origin, destination, api_key):
    # Build origin/destination strings prefer lat,lng
    origin_latlng = _extract_latlng(origin)
    dest_latlng = _extract_latlng(destination)

    if origin_latlng:
        origin_param = f"{origin_latlng[0]},{origin_latlng[1]}"
    else:
        origin_param = origin.get("address") or origin.get("name") or ""

    if dest_latlng:
        dest_param = f"{dest_latlng[0]},{dest_latlng[1]}"
    else:
        dest_param = destination.get("address") or destination.get("name") or ""

    params = {
        "origin": origin_param,
        "destination": dest_param,
        "mode": "driving",
        "key": api_key,
    }
    url = f"https://maps.googleapis.com/maps/api/directions/json?{urlencode(params)}"
    resp = requests.get(url, timeout=8)
    return resp


def get_google_travel_time(origin, destination):
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"success": False, "error": "missing_api_key"}

    try:
        resp = _call_google_directions(origin, destination, api_key)
    except Exception as e:
        return {"success": False, "error": "request_failed", "exception": str(e)}

    if resp.status_code != 200:
        return {"success": False, "error": "http_error", "status_code": resp.status_code}

    data = resp.json()
    status = data.get("status")
    if status != "OK":
        return {"success": False, "error": status, "raw": data}

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
    # Build keys
    origin_key = build_location_key(origin)
    destination_key = build_location_key(destination)

    # Try cache
    if should_use_cache(origin_key, destination_key):
        cached = get_travel_cache_record(origin_key, destination_key)
        if cached:
            return {
                "travel_minutes": int(cached.get("travel_minutes") or 0),
                "distance_text": cached.get("distance_text"),
                "duration_text": cached.get("duration_text"),
                "source": cached.get("source") or "cache",
                "warning": None,
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
            # On failure, fallback to fake but include warning
            fake = get_fake_travel_time(origin, destination)
            save_travel_cache_record(origin_key, destination_key, fake["travel_minutes"], fake.get("distance_text"), fake.get("duration_text"), "fake")
            warning = f"Google Maps 查詢失敗：{google_result.get('error')}，已使用假車程"
            return {"travel_minutes": fake["travel_minutes"], "distance_text": fake.get("distance_text"), "duration_text": fake.get("duration_text"), "source": "fake", "warning": warning}

    # real disabled, return fake
    fake = get_fake_travel_time(origin, destination)
    # do not save fake to cache unless desired; here we save to cache to speed repeat
    save_travel_cache_record(origin_key, destination_key, fake["travel_minutes"], fake.get("distance_text"), fake.get("duration_text"), "fake")
    return {"travel_minutes": fake["travel_minutes"], "distance_text": fake.get("distance_text"), "duration_text": fake.get("duration_text"), "source": "fake", "warning": None}

