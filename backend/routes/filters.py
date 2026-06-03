from flask import Blueprint, jsonify

from db import get_db

filters_bp = Blueprint("filters", __name__)


@filters_bp.get("/filters")
def api_get_filters():
    db = get_db()
    cur = db.cursor()

    def distinct(column):
        q = f"SELECT DISTINCT {column} FROM spots WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column} ASC"
        cur.execute(q)
        return [r[0] for r in cur.fetchall()]

    data = {
        "areas": distinct("area"),
        "trip_lengths": distinct("trip_length"),
        "categories": distinct("category"),
        "stay_types": distinct("stay_type"),
        "indoor_outdoor": distinct("indoor_outdoor"),
        "budgets": distinct("budget"),
    }

    return jsonify({"success": True, "data": data})
