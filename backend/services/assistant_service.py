import datetime
import json
import re

from flask import current_app

from db import get_db
from services.assistant_context import build_prompt
from services.itinerary_formatter import format_itinerary
from services.gemini_service import generate_text
from services.schedule_service import generate_itinerary


def _normalize_trip_length(value):
    if value in ("half_day", "半日"):
        return "半日"
    if value in ("full_day", "一日"):
        return "一日"
    return value or None


def _normalize_area(value):
    if value in (None, "", "不指定"):
        return None
    return value


def _normalize_preferences(value):
    if isinstance(value, list):
        return [item for item in value if item]
    if value:
        return [value]
    return []


def _split_values(value):
    if not value:
        return []
    parts = re.split(r"[、,，/\s]+", str(value).strip())
    return [part.strip() for part in parts if part and part.strip()]


def _clean_field_value(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text in ("", "(可不填)", "可不填", "不填", "無"):
        return ""
    return text


def _clean_origin_value(value):
    text = _clean_field_value(value)
    if not text:
        return None

    text = re.sub(r"(?:出發地|出發)$", "", text).strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _normalize_end_time_value(value):
    text = _clean_field_value(value)
    if not text:
        return ""

    patterns = [
        r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})$",
        r"^(?P<period>上午|下午|晚上)(?P<hour>\d{1,2})點(?P<minute>\d{1,2})?$",
        r"^(?P<hour>\d{1,2})點(?P<minute>\d{1,2})?$",
    ]

    match = None
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            break

    if not match:
        return ""

    hour = int(match.groupdict().get("hour") or 0)
    minute_text = match.groupdict().get("minute")
    minute = int(minute_text) if minute_text else 0
    period = match.groupdict().get("period")

    if period == "下午" and hour < 12:
        hour += 12
    elif period == "晚上" and hour < 12:
        hour += 12
    elif period == "上午" and hour == 12:
        hour = 0

    if hour > 23 or minute > 59:
        return ""

    return f"{hour:02d}:{minute:02d}"


def _extract_formatted_fields(message):
    if not message:
        return {}

    fields = {}
    label_map = {
        "出發地": "origin",
        "目的地/地區": "area",
        "日期": "date",
        "出發時間": "start_time",
        "結束時間": "end_time",
        "偏好": "preferences",
        "不要": "exclude_keywords",
        "備註": "notes",
    }

    for raw_line in message.splitlines():
        line = raw_line.strip()
        if not line or "：" not in line and ":" not in line:
            continue

        for label, key in label_map.items():
            if line.startswith(f"{label}：") or line.startswith(f"{label}:"):
                value = line.split("：", 1)[1].strip() if "：" in line else line.split(":", 1)[1].strip()
                fields[key] = value
                break

    if "不想去" in message and "exclude_keywords" not in fields:
        matches = re.findall(r"不想去\s*([^\n，,。；;]+)", message)
        if matches:
            fields["exclude_keywords"] = "、".join(matches)

    if "換方案" in message.strip():
        fields["change_plan"] = True

    return fields


def _normalize_exclude_keywords(value):
    return _split_values(value)


def _compose_keyword(area, preferences, notes):
    keyword_parts = []
    if area and area != "不指定":
        keyword_parts.append(area)
    for item in preferences or []:
        if item and item not in keyword_parts:
            keyword_parts.append(item)
    for item in notes or []:
        if item and item not in keyword_parts:
            keyword_parts.append(item)
    return keyword_parts or None


def _has_form_payload(data):
    return any(
        key in data
        for key in (
            "origin",
            "date",
            "start_date",
            "start_time",
            "end_date",
            "end_time",
        )
    )


def _build_trip_context(data, parsed_request):
    origin = (data.get("origin") or parsed_request.get("origin") or "").strip() or None
    date = (data.get("date") or data.get("start_date") or parsed_request.get("date") or "").strip()
    trip_length = _normalize_trip_length(data.get("trip_length") or parsed_request.get("trip_length"))
    start_time = (data.get("start_time") or parsed_request.get("start_time") or "09:00").strip() or "09:00"
    end_date = (data.get("end_date") or parsed_request.get("end_date") or date or "").strip()
    default_end_time = "13:00" if trip_length == "半日" else "17:00"
    end_time = (data.get("end_time") or parsed_request.get("end_time") or default_end_time or "").strip()
    preferences = _normalize_preferences(data.get("preferences") or parsed_request.get("preferences"))
    area = _normalize_area(data.get("area") or parsed_request.get("area"))
    exclude_keywords = _normalize_exclude_keywords(data.get("exclude_keywords") or parsed_request.get("exclude_keywords"))
    note_keywords = _split_values(data.get("notes") or parsed_request.get("notes"))

    return {
        "origin": origin,
        "date": date,
        "start_time": start_time,
        "end_date": end_date,
        "end_time": end_time,
        "trip_length": trip_length,
        "area": area,
        "preferences": preferences,
        "exclude_keywords": exclude_keywords,
        "note_keywords": note_keywords,
    }


def _apply_trip_context(parsed_request, trip_context):
    parsed_request = dict(parsed_request)
    parsed_request["origin"] = trip_context.get("origin")
    parsed_request["date"] = trip_context.get("date")
    parsed_request["start_time"] = trip_context.get("start_time")
    parsed_request["end_date"] = trip_context.get("end_date")
    parsed_request["end_time"] = trip_context.get("end_time")
    parsed_request["trip_length"] = trip_context.get("trip_length") or parsed_request.get("trip_length")
    parsed_request["area"] = trip_context.get("area") or parsed_request.get("area")
    parsed_request["exclude_keywords"] = trip_context.get("exclude_keywords") or parsed_request.get("exclude_keywords") or []
    parsed_request["notes"] = trip_context.get("note_keywords") or parsed_request.get("notes") or []

    preferences = trip_context.get("preferences") or []
    if preferences:
        parsed_request["preferences"] = preferences
        if not parsed_request.get("type"):
            for preference in preferences:
                if preference in ("親子", "DIY", "咖啡", "茶", "生態"):
                    parsed_request["type"] = preference
                    break
        if not parsed_request.get("indoor_outdoor"):
            if "室內" in preferences:
                parsed_request["indoor_outdoor"] = "室內"
            elif "戶外" in preferences:
                parsed_request["indoor_outdoor"] = "戶外"

    start_date = trip_context.get("date")
    start_time = trip_context.get("start_time")
    end_date = trip_context.get("end_date") or start_date
    end_time = trip_context.get("end_time")
    if start_date and start_time:
        parsed_request["start_datetime"] = f"{start_date} {start_time}"
    if end_date and end_time:
        parsed_request["end_datetime"] = f"{end_date} {end_time}"

    parsed_request["keyword"] = _compose_keyword(
        parsed_request.get("area"),
        parsed_request.get("preferences"),
        parsed_request.get("notes"),
    )

    return parsed_request


def _prepend_trip_summary(text, trip_context):
    summary_lines = []
    origin = trip_context.get("origin")
    date = trip_context.get("date")
    start_time = trip_context.get("start_time")

    if origin:
        summary_lines.append(f"出發地點：{origin}")
    else:
        summary_lines.append("未提供出發地，僅安排景點內行程，不計算出發車程。")
    if date:
        summary_lines.append(f"出發日期：{date}")
    if start_time:
        summary_lines.append(f"出發時間：{start_time}")

    if not summary_lines:
        return text

    summary = "\n".join(summary_lines)
    if text.startswith(summary_lines[0]):
        return text
    return summary + "\n\n" + text


AREA_RULES = [
    ("小半天", ["小半天", "小半天地區"]),
    ("大雁", ["大雁"]),
    ("糯米橋", ["糯米橋"]),
]

TYPE_RULES = [
    ("親子", ["親子", "小孩", "兒童", "家庭"]),
    ("DIY", ["DIY", "手作", "體驗"]),
    ("咖啡", ["咖啡", "下午茶", "甜點"]),
    ("茶", ["茶", "茶園", "品茶"]),
    ("生態", ["生態", "自然", "自然教育", "步道"]),
]

PREFERENCE_RULES = [
    ("不要戶外", ["不要戶外", "室內", "不想戶外", "不要室外"]),
    ("自然教育", ["自然教育"]),
    ("室內", ["室內"]),
]

DURATION_RULES = [
    ("半日", ["半日", "半天", "半日遊", "半天遊"]),
    ("一日", ["一日", "一日遊", "整天"]),
]

ITINERARY_INTENT_RULES = [
    "行程",
    "安排",
    "規劃",
    "一日",
    "半日",
    "遊玩",
    "親子行程",
]


def _first_rule_match(message, rules):
    for canonical, keywords in rules:
        if any(keyword in message for keyword in keywords):
            return canonical
    return None


def _parse_user_request(message, data):
    def _match_origin(text):
        if not text:
            return None

        patterns = [
            r"從\s*(.+?)\s*出發",
            r"我想從\s*(.+?)\s*出發",
            r"(?:我想)?(?:從)?(.{2,40}?)\s*出發",
    ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                origin_text = match.group(1).strip()
                origin_text = re.sub(r"[，,。；;]$", "", origin_text).strip()
                if origin_text:
                    return origin_text
        return None

    def _match_area(text):
        if not text:
            return None

        area_keywords = ["清境", "小半天", "大雁", "糯米橋", "桃米", "車埕"]
        for keyword in area_keywords:
            if keyword in text:
                return keyword
        return None

    def _normalize_hhmm(hour, minute, period=None):
        try:
            hour = int(hour)
            minute = int(minute or 0)
        except Exception:
            return ""

        if period in ("下午", "晚上") and hour < 12:
            hour += 12
        elif period == "上午" and hour == 12:
            hour = 0
        elif period == "早上" and hour == 12:
            hour = 0

        if hour > 23 or minute > 59:
            return ""
        return f"{hour:02d}:{minute:02d}"

    def _match_start_time(text):
        if not text:
            return None

        patterns = [
            r"(?P<period>早上|上午|中午|下午|晚上)\s*(?P<hour>\d{1,2})(?:[:點](?P<minute>\d{1,2}))?\s*點?(?:出門|出發)?",
            r"(?P<hour>\d{1,2}):(?P<minute>\d{2})",
            r"(?P<hour>\d{1,2})點(?P<minute>\d{1,2})?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groupdict()
                time_text = _normalize_hhmm(groups.get("hour"), groups.get("minute"), groups.get("period"))
                if time_text:
                    return time_text
        return None

    def _match_end_time(text):
        if not text:
            return None

        patterns = [
            r"(?P<period>早上|上午|中午|下午|晚上)\s*(?P<hour>\d{1,2})(?:[:點](?P<minute>\d{1,2}))?\s*點?前",
            r"(?P<hour>\d{1,2}):(?P<minute>\d{2})",
            r"(?P<period>早上|上午|中午|下午|晚上)\s*(?P<hour>\d{1,2})點(?P<minute>\d{1,2})?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groupdict()
                time_text = _normalize_hhmm(groups.get("hour"), groups.get("minute"), groups.get("period"))
                if time_text:
                    return time_text
        return None

    def _match_trip_length(text):
        if not text:
            return None

        patterns = [
            (r"三天兩夜", "三天兩夜"),
            (r"兩天一夜", "兩天一夜"),
            (r"一日", "一日"),
            (r"半日", "半日"),
        ]
        for pattern, value in patterns:
            if re.search(pattern, text):
                return value
        return None

    message_text = message or ""
    message_trip_length = _match_trip_length(message_text)
    message_origin = _match_origin(message_text)
    message_area = _match_area(message_text)
    message_start_time = _match_start_time(message_text)
    message_end_time = _match_end_time(message_text)

    if _has_form_payload(data):
        formatted = _extract_formatted_fields(message)
        origin = _clean_origin_value(data.get("origin")) or message_origin
        date = _clean_field_value(data.get("date") or data.get("start_date"))
        start_time = _clean_field_value(data.get("start_time")) or message_start_time or "09:00"
        end_time = _normalize_end_time_value(data.get("end_time")) or message_end_time
        area = _clean_field_value(formatted.get("area")) or _first_rule_match(message_text, AREA_RULES) or message_area
        if area == "不指定":
            area = None

        preference_values = _split_values(formatted.get("preferences"))
        if not preference_values:
            matched_preference = _first_rule_match(message, PREFERENCE_RULES)
            if matched_preference:
                preference_values = [matched_preference]

        travel_type = None
        for preference in preference_values:
            if preference in ("親子", "DIY", "咖啡", "茶", "生態"):
                travel_type = preference
                break

        note_keywords = _split_values(formatted.get("notes"))
        exclude_keywords = _normalize_exclude_keywords(formatted.get("exclude_keywords"))
        keyword = _compose_keyword(area, preference_values, note_keywords)

        trip_length = _normalize_trip_length(data.get("trip_length") or message_trip_length)

        parsed = {
            "area": area,
            "type": travel_type,
            "duration": trip_length,
            "preference": preference_values[0] if preference_values else None,
            "preferences": preference_values,
            "exclude_keywords": exclude_keywords,
            "notes": note_keywords,
            "keyword": keyword,
            "trip_length": trip_length,
            "origin": origin,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "start_date": date,
            "end_date": _clean_field_value(data.get("end_date")),
            "end_datetime": data.get("end_datetime"),
            "origin_latitude": data.get("origin_latitude"),
            "origin_longitude": data.get("origin_longitude"),
        }

        print("[assistant] parsed origin =", parsed.get("origin"))
        print("[assistant] parsed area =", parsed.get("area"))
        print("[assistant] parsed start_time =", parsed.get("start_time"))
        print("[assistant] parsed end_time =", parsed.get("end_time"))
        print("[assistant] parsed trip_length =", parsed.get("trip_length"))

        return parsed

    formatted = _extract_formatted_fields(message)
    area = message_area or _first_rule_match(message_text, AREA_RULES)
    travel_type = _first_rule_match(message_text, TYPE_RULES)
    duration = message_trip_length or _first_rule_match(message_text, DURATION_RULES)
    preference = _first_rule_match(message, PREFERENCE_RULES)

    area = _clean_field_value(formatted.get("area")) or area
    if area == "不指定":
        area = None

    preference_values = _split_values(formatted.get("preferences"))
    if not preference_values and preference:
        preference_values = [preference]

    exclude_keywords = _normalize_exclude_keywords(formatted.get("exclude_keywords"))
    note_keywords = _split_values(formatted.get("notes"))

    origin = _clean_origin_value(formatted.get("origin")) or message_origin or None
    date = _clean_field_value(formatted.get("date"))
    start_time = _clean_field_value(formatted.get("start_time")) or message_start_time or "09:00"
    end_time = _normalize_end_time_value(formatted.get("end_time")) or message_end_time

    keyword = _compose_keyword(area, preference_values, note_keywords)

    trip_length = _normalize_trip_length(duration or message_trip_length)

    parsed = {
        "area": area,
        "type": travel_type,
        "duration": duration,
        "preference": preference,
        "preferences": preference_values,
        "exclude_keywords": exclude_keywords,
        "notes": note_keywords,
        "keyword": keyword,
        "trip_length": trip_length,
        "origin": origin or data.get("origin") or None,
        "date": date or data.get("date") or data.get("start_date") or "",
        "start_date": date or data.get("start_date") or data.get("date") or "",
        "start_time": start_time or data.get("start_time") or "09:00",
        "end_time": end_time or data.get("end_time") or "",
        "end_date": _clean_field_value(formatted.get("end_date") or data.get("end_date")),
        "end_datetime": data.get("end_datetime"),
        "origin_latitude": data.get("origin_latitude"),
        "origin_longitude": data.get("origin_longitude"),
    }

    if preference == "不要戶外":
        parsed["indoor_outdoor"] = "室內"

    if formatted.get("change_plan"):
        parsed["change_plan"] = True

    print("[assistant] parsed origin =", parsed.get("origin"))
    print("[assistant] parsed area =", parsed.get("area"))
    print("[assistant] parsed start_time =", parsed.get("start_time"))
    print("[assistant] parsed end_time =", parsed.get("end_time"))
    print("[assistant] parsed trip_length =", parsed.get("trip_length"))

    return parsed


def _detect_intent(message, parsed_request):
    if (
        parsed_request.get("origin")
        or parsed_request.get("date")
        or parsed_request.get("start_time")
        or parsed_request.get("end_date")
        or parsed_request.get("end_time")
    ):
        return "itinerary"
    if parsed_request.get("area") or parsed_request.get("type"):
        return "itinerary"
    if any(keyword in message for keyword in ITINERARY_INTENT_RULES):
        return "itinerary"
    return "unknown"


def generate_assistant_response(message, data=None, platform="web"):
    data = data or {}
    message = message or ""

    parsed_request = _parse_user_request(message, data)
    trip_context = _build_trip_context(data, parsed_request)
    parsed_request = _apply_trip_context(parsed_request, trip_context)
    intent = _detect_intent(message, parsed_request)

    if parsed_request.get("change_plan"):
        return {
            "success": True,
            "text": "請告訴我想保留哪些條件，以及不想去哪些地點。",
            "raw": {"source": "rule_based_fallback"},
        }

    if not message and intent != "itinerary":
        message = "請依據行程條件安排行程。"

    if parsed_request.get("origin") is None:
        no_origin_notice = "未提供出發地，僅安排景點間行程。"
    else:
        no_origin_notice = None

    itinerary_payload = {
        "area": parsed_request.get("area"),
        "type": parsed_request.get("type"),
        "trip_length": parsed_request.get("trip_length"),
        "keyword": parsed_request.get("keyword"),
        "indoor_outdoor": parsed_request.get("indoor_outdoor"),
        "date": trip_context.get("date") or parsed_request.get("date"),
        "start_date": trip_context.get("start_date") or trip_context.get("date") or parsed_request.get("start_date") or parsed_request.get("date"),
        "origin": trip_context.get("origin"),
        "start_point": trip_context.get("origin"),
        "start_time": trip_context.get("start_time"),
        "start_datetime": parsed_request.get("start_datetime"),
        "end_datetime": parsed_request.get("end_datetime"),
        "end_date": trip_context.get("end_date"),
        "end_time": trip_context.get("end_time"),
        "exclude_keywords": parsed_request.get("exclude_keywords") or [],
        "origin_latitude": parsed_request.get("origin_latitude"),
        "origin_longitude": parsed_request.get("origin_longitude"),
        "limit": 12,
    }

    db = get_db()
    now = datetime.datetime.now().isoformat(timespec="seconds")

    if intent == "itinerary":
        try:
            itinerary_result = generate_itinerary(itinerary_payload)
            formatter_text = format_itinerary(message, parsed_request, trip_context, itinerary_result, platform=platform)
            if no_origin_notice and no_origin_notice not in formatter_text:
                formatter_text = no_origin_notice + "\n\n" + formatter_text

            try:
                db.execute(
                    "INSERT INTO query_logs (platform, raw_text, parsed_json, result_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        platform,
                        message,
                        json.dumps({"parsed_request": parsed_request, "itinerary_result": itinerary_result}, ensure_ascii=False),
                        json.dumps({"text": formatter_text, "meta": {"source": "itinerary_formatter"}}, ensure_ascii=False),
                        now,
                    ),
                )
                db.commit()
            except Exception:
                current_app.logger.exception("failed to write query_log")

            return {"success": True, "text": formatter_text, "raw": {"source": "itinerary_formatter"}}
        except Exception:
            current_app.logger.exception("itinerary flow failed")
            return {"success": False, "error": "itinerary flow failed"}

    prompt = build_prompt(message, platform=platform, trip_context=trip_context)
    gen = generate_text(prompt)
    if not gen.get("success") or not gen.get("text"):
        text = "我好像沒看懂您的意思。"
        gen = {"success": True, "text": text, "raw": {"source": "rule_based_fallback"}, "error": None}

    gen["text"] = _prepend_trip_summary(gen.get("text") or "", trip_context)

    try:
        db.execute(
            "INSERT INTO query_logs (platform, raw_text, parsed_json, result_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                platform,
                message,
                json.dumps({"parsed_request": parsed_request, "itinerary_result": None}, ensure_ascii=False),
                json.dumps({"text": gen.get("text"), "meta": gen.get("raw")}, ensure_ascii=False),
                now,
            ),
        )
        db.commit()
    except Exception:
        current_app.logger.exception("failed to write query_log")

    return {"success": True, "text": gen.get("text"), "raw": gen.get("raw")}