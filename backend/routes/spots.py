from flask import Blueprint, jsonify, request

from models.spot_model import get_spot_by_id, list_spots

spots_bp = Blueprint("spots", __name__)


@spots_bp.get("/spots")
def api_list_spots():
    filters = {
        "area": request.args.get("area") or request.args.get("region"),
        "category": request.args.get("category") or request.args.get("activity_type"),
        "trip_length": request.args.get("trip_length") or request.args.get("duration"),
        "stay_type": request.args.get("stay_type") or request.args.get("stay_level"),
        "indoor_outdoor": request.args.get("indoor_outdoor") or request.args.get("space"),
        "budget": request.args.get("budget") or request.args.get("budget_level"),
        "keyword": request.args.get("keyword"),
        "limit": request.args.get("limit"),
    }
    spots = list_spots(filters)
    return jsonify({"success": True, "data": spots})


@spots_bp.get("/spots/<int:spot_id>")
def api_get_spot(spot_id):
    spot = get_spot_by_id(spot_id)
    if not spot:
        return jsonify({"success": False, "error": "spot not found"}), 404
    return jsonify(spot)

