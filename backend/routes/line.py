from flask import Blueprint, jsonify, request

from services.line_service import build_line_reply, parse_fixed_format

line_bp = Blueprint("line", __name__)


@line_bp.post("/line/webhook")
def api_line_webhook():
    payload = request.get_json(force=True, silent=True) or {}
    text = payload.get("text", "")
    reply = build_line_reply(text)
    return jsonify(reply)


@line_bp.post("/line/parse")
def api_line_parse():
    payload = request.get_json(force=True, silent=True) or {}
    return jsonify(parse_fixed_format(payload.get("text", "")))

