from flask import Blueprint, jsonify, request

from services.news_service import get_latest_news_payload, refresh_latest_news


news_bp = Blueprint("news", __name__)


@news_bp.get("/news/latest")
def api_latest_news():
    limit = request.args.get("limit", 5)
    try:
        # allow up to 30 items (frontend may paginate client-side)
        limit = max(1, min(int(limit), 30))
    except (TypeError, ValueError):
        limit = 5

    try:
        news_items = get_latest_news_payload(limit=limit)
    except Exception as error:
        return jsonify({"success": False, "error": str(error), "data": []}), 502

    return jsonify({"success": True, "data": news_items, "source": "https://travel.nantou.gov.tw/category/news-press/feed/"})


@news_bp.post("/news/refresh")
def api_refresh_news():
    try:
        news_items = refresh_latest_news(force=True)
    except Exception as error:
        return jsonify({"success": False, "error": str(error), "data": []}), 502

    return jsonify({"success": True, "data": news_items})