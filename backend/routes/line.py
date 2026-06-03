from flask import Blueprint, jsonify, request

from services.line_service import parse_fixed_format, process_line_webhook_request

line_bp = Blueprint("line", __name__)


@line_bp.route("/callback", methods=["GET"])
def callback_health():
    return jsonify({"ok": True, "message": "LINE callback ready"})


@line_bp.route("/line/webhook", methods=["GET"])
def line_webhook_health():
    return jsonify({"ok": True, "message": "LINE webhook ready"})


@line_bp.route("/callback", methods=["POST"])
@line_bp.route("/line/webhook", methods=["POST"])
def api_line_webhook():
    result = process_line_webhook_request(
    request.get_data(),
    request.headers,
    reply_to_line=True,
    require_signature=False
)
    return jsonify(result), result.get("status_code", 200)


@line_bp.post("/line/parse")
def api_line_parse():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify(parse_fixed_format(payload.get("text", "")))

