from flask import Blueprint, jsonify, request, current_app

from models.spot_model import get_spot_by_id
from services.maps_service import get_travel_time

maps_bp = Blueprint("maps", __name__)


@maps_bp.post("/maps/travel-time")
def api_travel_time():
    payload = request.get_json(force=True, silent=True) or {}
    origin_id = payload.get("origin_spot_id")
    destination_id = payload.get("destination_spot_id")

    origin = get_spot_by_id(origin_id) if origin_id else payload.get("origin")
    destination = get_spot_by_id(destination_id) if destination_id else payload.get("destination")

    if not origin or not destination:
        return jsonify({"success": False, "error": "origin or destination missing"}), 400

    result = get_travel_time(origin, destination)
    # result: {travel_minutes, distance_text, duration_text, source, warning}
    response = {
        "success": True,
        "travel_minutes": int(result.get("travel_minutes") or 0),
        "distance_text": result.get("distance_text"),
        "duration_text": result.get("duration_text"),
        "source": result.get("source"),
        "warning": result.get("warning"),
    }
    return jsonify(response)

