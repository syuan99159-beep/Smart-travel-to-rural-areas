from flask import Blueprint, jsonify, request

from models.itinerary_model import create_itinerary, get_itinerary
from services.schedule_service import generate_itinerary

itineraries_bp = Blueprint("itineraries", __name__)


@itineraries_bp.post("/itineraries/generate")
def api_generate_itinerary():
    payload = request.get_json(force=True, silent=True) or {}
    result = generate_itinerary(payload)

    if not result.get("success"):
        return jsonify(result), 400

    itinerary_payload = {
        **payload,
        **result["summary"],
        "is_rushed": result.get("is_too_rushed", False),
        "rush_reason": result.get("warnings", []),
        "start_point": payload.get("start_point") or payload.get("origin") or "南投車站",
    }
    itinerary_id = create_itinerary(itinerary_payload, result["items"])
    result["itinerary_id"] = itinerary_id
    return jsonify(result)


@itineraries_bp.get("/itineraries/<int:itinerary_id>")
def api_get_itinerary(itinerary_id):
    itinerary = get_itinerary(itinerary_id)
    if not itinerary:
        return jsonify({"error": "itinerary not found"}), 404
    return jsonify(itinerary)

