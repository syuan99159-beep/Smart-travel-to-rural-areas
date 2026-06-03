import base64
import hashlib
import hmac
import json
import os

import requests
from flask import current_app

from services.assistant_service import generate_assistant_response


LINE_REPLY_API = "https://api.line.me/v2/bot/message/reply"


REGIONS = ["小半天", "大雁", "糯米橋"]
ACTIVITY_TYPES = ["DIY", "親子", "食農教育", "生態導覽", "戶外", "咖啡"]
DURATION_MAP = {"半日": "half_day", "一日": "full_day"}
STAY_LEVEL_MAP = {"短": "short", "中": "medium", "長": "long"}


def parse_fixed_format(text):
    normalized = " ".join((text or "").split())
    tokens = normalized.split(" ") if normalized else []

    filters = {
        "raw_text": normalized,
        "region": None,
        "activity_type": None,
        "itinerary_length": None,
        "stay_level": None,
        "budget_level": None,
        "indoor_outdoor": None,
        "keyword": None,
    }

    keywords = []
    for token in tokens:
        if token in REGIONS:
            filters["region"] = token
            continue
        if token in ACTIVITY_TYPES:
            filters["activity_type"] = token
            continue
        if token in DURATION_MAP:
            filters["itinerary_length"] = DURATION_MAP[token]
            continue
        if token in STAY_LEVEL_MAP:
            filters["stay_level"] = token
            continue
        if token in ("不要戶外", "不要室內"):
            filters["indoor_outdoor"] = "室內"
            continue
        if token == "戶外":
            filters["indoor_outdoor"] = "戶外"
            continue
        if token == "室內":
            filters["indoor_outdoor"] = "室內"
            continue
        if token in ("低預算", "中預算", "高預算"):
            filters["budget_level"] = token.replace("預算", "")
            continue
        keywords.append(token)

    if keywords:
        filters["keyword"] = " ".join(keywords)

    missing = []
    if not filters["itinerary_length"]:
        missing.append("行程長度（半日 / 一日）")

    return {
        "filters": filters,
        "missing": missing,
        "is_complete": len(missing) == 0,
    }


def build_line_reply(text):
    assistant_result = generate_assistant_response(text, platform="line")
    reply_text = assistant_result.get("text") or "我好像沒看懂您的意思。"
    return {
        "success": assistant_result.get("success", False),
        "text": reply_text,
        "messages": build_line_messages(reply_text),
        "assistant": assistant_result,
    }


def split_text_for_line(text, max_length=4500, max_messages=5):
    normalized = (text or "").strip()
    if not normalized:
        return ["我好像沒看懂您的意思。"]

    chunks = []
    remaining = normalized

    while remaining:
        if len(chunks) >= max_messages:
            chunks[-1] = chunks[-1] + "\n\n（內容過長，已截斷，請改用網頁版查看完整內容。）"
            break

        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        cut = remaining.rfind("\n", 0, max_length)
        if cut < 0 or cut < max_length // 2:
            cut = max_length

        chunk = remaining[:cut].rstrip()
        if not chunk:
            chunk = remaining[:max_length]
            cut = max_length

        chunks.append(chunk)
        remaining = remaining[cut:].lstrip()

    return chunks


def build_line_messages(text):
    return [{"type": "text", "text": chunk} for chunk in split_text_for_line(text)]


def send_line_reply(reply_token, text):
    channel_access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not channel_access_token:
        return {"success": False, "error": "LINE_CHANNEL_ACCESS_TOKEN not set"}

    print("[line] replying message")
    print("[line] reply_token =", reply_token)
    print("[line] text length =", len(text or ""))

    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": (text or "")[:5000],
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {channel_access_token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(LINE_REPLY_API, headers=headers, json=payload, timeout=20)
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    if not resp.ok:
        print(resp.status_code)
        print(resp.text)
        return {"success": False, "status_code": resp.status_code, "error": resp.text}

    return {"success": True, "status_code": resp.status_code}


def _verify_line_signature(raw_body, signature):
    channel_secret = os.environ.get("LINE_CHANNEL_SECRET", "")
    if not channel_secret:
        return False

    digest = hmac.new(channel_secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature or "")


def _reply_to_line(reply_token, messages):
    if not messages:
        return {"success": False, "error": "no messages to reply"}

    text = messages[0].get("text") if isinstance(messages[0], dict) else ""
    return send_line_reply(reply_token, text)


def process_line_webhook_request(raw_body, headers, reply_to_line=False, require_signature=False):
    raw_body = raw_body or b""
    signature = headers.get("X-Line-Signature") if headers else None

    if require_signature and not _verify_line_signature(raw_body, signature):
        return {"success": False, "error": "invalid LINE signature", "status_code": 403}

    try:
        payload_text = raw_body.decode("utf-8") if raw_body else "{}"
        payload = json.loads(payload_text or "{}")
    except Exception:
        return {"success": False, "error": "invalid JSON payload", "status_code": 400}

    if isinstance(payload, dict) and payload.get("events") is not None:
        events = payload.get("events") or []
        results = []

        for event in events:
            if event.get("type") != "message":
                continue

            message = event.get("message") or {}
            if message.get("type") != "text":
                continue

            reply_token = event.get("replyToken")
            user_text = message.get("text", "")
            assistant_result = generate_assistant_response(user_text, platform="line")
            response_text = assistant_result.get("response") or assistant_result.get("text") or "我好像沒看懂您的意思。"
            messages = build_line_messages(response_text)

            reply_result = {"success": True, "skipped": True}
            if reply_to_line and assistant_result.get("success"):
                reply_result = send_line_reply(reply_token, response_text)

            results.append(
                {
                    "event_type": event.get("type"),
                    "message_type": message.get("type"),
                    "reply_token_present": bool(reply_token),
                    "assistant": assistant_result,
                    "reply": reply_result,
                    "messages": messages,
                }
            )

        return {"success": True, "handled_events": len(results), "results": results, "status_code": 200}

    if isinstance(payload, dict):
        preview_text = payload.get("text", "")
    else:
        preview_text = ""

    preview = build_line_reply(preview_text)
    return {
        "success": preview.get("success", False),
        "text": preview.get("text", ""),
        "messages": preview.get("messages", []),
        "assistant": preview.get("assistant"),
        "status_code": 200,
    }

