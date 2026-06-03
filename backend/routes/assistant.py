from flask import Blueprint, request, jsonify

from services.assistant_service import generate_assistant_response

assistant_bp = Blueprint("assistant_bp", __name__)
print("[assistant] loaded file =", __file__)


@assistant_bp.route("/assistant/message", methods=["POST"])
def assistant_message():
    data = request.get_json() or {}
    message = data.get("message", "")
    platform = data.get("platform", "web")

    print("[assistant] route hit")
    print("[assistant] user message =", message)

    if not message:
        return jsonify({"success": False, "error": "missing message"}), 400

    result = generate_assistant_response(message, data=data, platform=platform)
    status_code = 200 if result.get("success") else 500
    return jsonify(result), status_code
