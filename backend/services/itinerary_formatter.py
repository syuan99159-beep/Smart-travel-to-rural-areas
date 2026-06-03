import json
import re
from datetime import datetime

from services.gemini_service import generate_text


def _normalize_trip_length(value):
    if value in ("half_day", "半日"):
        return "半日"
    if value in ("full_day", "一日"):
        return "一日"
    return value or ""


def _format_time_label(value):
    if not value:
        return ""

    text = str(value).strip()
    for time_format in ("%Y-%m-%d %H:%M", "%H:%M"):
        try:
            parsed = datetime.strptime(text, time_format)
            return parsed.strftime("%H:%M")
        except Exception:
            continue
    return text


def _route_source_label(source):
    mapping = {
        "google_maps": "Google Maps",
        "fallback_maps": "系統估算",
        "same_place": "同一地點",
        "originless": "景點內行程",
    }
    return mapping.get(source, "系統估算")


def _route_travel_text(item):
    duration_text = item.get("duration_text")
    if duration_text:
        return duration_text
    source = item.get("source")
    if source in ("Google Maps", "google_maps"):
        return f"約 {item.get('travel_minutes', 0)} 分鐘"
    if source in ("同一地點", "same_place"):
        return "同一地點，無需移動"
    return "目前使用系統估算車程"


def _clean_json_text(text):
    if not text:
        return ""

    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _extract_json_payload(text):
    cleaned = _clean_json_text(text)
    if not cleaned:
        return None

    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None


def _fallback_activity_descriptions(spot_items):
    return [item.get("description") or "此景點提供戶外活動與自然體驗。" for item in spot_items]


def _fallback_arrangement_reason(parsed_request, trip_context, itinerary_result):
    parts = []
    area = parsed_request.get("area") or trip_context.get("area")
    preferences = parsed_request.get("preferences") or trip_context.get("preferences") or []

    if area:
        parts.append(f"依據地區條件「{area}" + "」安排鄰近景點，減少不必要的移動。")
    if preferences:
        parts.append(f"並優先符合使用者偏好：{'、'.join(preferences)}。")
    if not parts:
        parts.append("依據使用者提供的條件與景點可用性安排可執行行程。")
    return "".join(parts)


def _fallback_route_rationale(itinerary_result):
    items = itinerary_result.get("items") or []
    if any(item.get("source") == "google_maps" for item in items):
        return "已依 Google Maps 驗證車程安排景點順序。"
    if any(item.get("source") == "fallback_maps" for item in items):
        return "目前使用系統估算車程安排景點順序。"
    if any(item.get("source") == "same_place" for item in items):
        return "景點彼此接近，安排以同一地點或步行可達為主。"
    if any(item.get("source") == "originless" for item in items):
        return "未提供出發地，僅安排景點內行程，不計算出發車程。"
    return "已依可用路線資訊安排景點順序。"


def _collect_warnings(itinerary_result):
    warnings = []
    for warning in itinerary_result.get("warnings") or []:
        if warning and warning not in warnings:
            warnings.append(warning)
    return warnings


def _parse_item_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M")
    except Exception:
        return None


def _group_items_by_day(items):
    grouped = []
    day_lookup = {}

    for item in items:
        item_dt = _parse_item_datetime(item.get("start_time")) or _parse_item_datetime(item.get("end_time"))
        if not item_dt:
            continue

        day_key = item_dt.date().isoformat()
        if day_key not in day_lookup:
            day_lookup[day_key] = []
            grouped.append((day_key, day_lookup[day_key]))
        day_lookup[day_key].append(item)

    return grouped


def _format_trip_title(trip_label):
    label = _normalize_trip_length(trip_label or "一日")
    if label in ("半日", "一日"):
        return f"{label}智慧行程"
    return f"{label}智慧行程"


def _build_ai_content(message, parsed_request, trip_context, itinerary_result):
    spot_items = [item for item in itinerary_result.get("items") or [] if item.get("type") == "spot"]
    prompt_payload = {
        "message": message,
        "parsed_request": parsed_request,
        "trip_context": trip_context,
        "itinerary_data": {
            "summary": itinerary_result.get("summary") or {},
            "items": spot_items,
            "warnings": itinerary_result.get("warnings") or [],
        },
        "output": {
            "activity_descriptions": "array aligned with spot_items order",
            "arrangement_reason": "short paragraph",
            "route_rationale": "short paragraph",
            "json_only": True,
            "no_markdown": True,
            "must_keep_fields": ["name", "address", "start_time", "end_time", "stay_minutes", "travel_from", "duration_text", "source"],
            "allowed_rewrites": ["description", "arrangement_reason", "route_rationale"],
        },
    }

    prompt = "\n".join([
        "你是智慧行程內容撰寫器。你只能使用提供的 itinerary_data JSON，且這份資料已經由後端完成車程與路線計算。",
        "禁止新增景點、修改景點名稱、地址、停留時間、車程、路線來源，或編造 Google Maps 結果。",
        "你只能在不改動既有欄位的前提下，潤飾 description、行程安排原因、路線合理性說明。",
        "請根據下列資料撰寫內容並只輸出 JSON：",
        json.dumps(prompt_payload, ensure_ascii=False, indent=2),
        "JSON 必須包含 activity_descriptions, arrangement_reason, route_rationale 三個欄位。",
    ])

    result = generate_text(prompt, max_output_tokens=600, temperature=0.2)
    if not result.get("success") or not result.get("text"):
        return {
            "activity_descriptions": _fallback_activity_descriptions(spot_items),
            "arrangement_reason": _fallback_arrangement_reason(parsed_request, trip_context, itinerary_result),
            "route_rationale": _fallback_route_rationale(itinerary_result),
        }

    payload = _extract_json_payload(result.get("text")) or {}
    activity_descriptions = payload.get("activity_descriptions") or _fallback_activity_descriptions(spot_items)
    if not isinstance(activity_descriptions, list):
        activity_descriptions = _fallback_activity_descriptions(spot_items)

    if len(activity_descriptions) < len(spot_items):
        activity_descriptions = activity_descriptions + _fallback_activity_descriptions(spot_items[len(activity_descriptions):])

    return {
        "activity_descriptions": [str(item).strip() or "此景點提供戶外活動與自然體驗。" for item in activity_descriptions[: len(spot_items)]],
        "arrangement_reason": str(payload.get("arrangement_reason") or _fallback_arrangement_reason(parsed_request, trip_context, itinerary_result)).strip(),
        "route_rationale": str(payload.get("route_rationale") or _fallback_route_rationale(itinerary_result)).strip(),
    }


def format_itinerary(message, parsed_request, trip_context, itinerary_result, platform="web"):
    parsed_request = parsed_request or {}
    trip_context = trip_context or {}
    itinerary_result = itinerary_result or {}

    origin = trip_context.get("origin") or parsed_request.get("origin")
    date = trip_context.get("date") or parsed_request.get("date") or ""
    start_time = trip_context.get("start_time") or parsed_request.get("start_time") or "09:00"
    end_date = trip_context.get("end_date") or parsed_request.get("end_date") or ""
    end_time = trip_context.get("end_time") or parsed_request.get("end_time") or ""
    trip_length = itinerary_result.get("summary", {}).get("trip_length") or trip_context.get("trip_length") or parsed_request.get("trip_length") or "一日"
    area = trip_context.get("area") or parsed_request.get("area") or ""
    warnings = _collect_warnings(itinerary_result)

    title = _format_trip_title(trip_length)

    ai_content = _build_ai_content(message, parsed_request, trip_context, itinerary_result)
    activity_descriptions = ai_content.get("activity_descriptions") or []

    summary = itinerary_result.get("summary") or {}
    trip_type_label = summary.get("duration_label") or trip_length

    lines = [
        "## 行程名稱",
        title,
        "",
        "## 出發資訊",
    ]

    if origin:
        lines.append(f"- 出發地點：{origin}")
    else:
        lines.append("- 未提供出發地，僅安排景點內行程，不計算出發車程。")
    if date:
        lines.append(f"- 出發日期：{date}")
    if start_time:
        lines.append(f"- 出發時間：{_format_time_label(start_time) or start_time}")
    if end_date:
        lines.append(f"- 結束日期：{end_date}")
    if end_time:
        lines.append(f"- 結束時間：{_format_time_label(end_time) or end_time}")
    lines.append(f"- 行程類型：{trip_type_label}")

    lines.extend([
        "",
        "## 建議行程",
    ])

    items = itinerary_result.get("items") or []
    if not items:
        lines.append("- 目前找不到符合條件的景點。")
    else:
        grouped_items = _group_items_by_day(items)
        spot_index = 0
        for day_index, (_, day_items) in enumerate(grouped_items, start=1):
            lines.extend(["", f"# Day {day_index}"])
            for item in day_items:
                item_type = item.get("type")
                start_label = _format_time_label(item.get("start_time"))
                end_label = _format_time_label(item.get("end_time"))
                time_text = f"{start_label} - {end_label}" if start_label and end_label else start_label or end_label or ""

                if item_type == "spot":
                    activity_description = activity_descriptions[spot_index] if spot_index < len(activity_descriptions) else "此景點提供戶外活動與自然體驗。"
                    spot_index += 1
                    lines.append(f"- {time_text} {item.get('name', '未知景點')}")
                    if item.get("address"):
                        lines.append(f"  - 地址：{item.get('address')}")
                    lines.append(f"  - 停留時間：{item.get('stay_minutes', 0)} 分鐘")
                    if item.get("travel_from"):
                        lines.append(f"  - 車程：{item.get('travel_from')} → {item.get('name', '未知景點')}")
                    lines.append(f"    {item.get('duration_text') or _route_travel_text(item)}")
                    lines.append(f"  - 路線來源：{_route_source_label(item.get('source'))}")
                    lines.append(f"  - 活動說明：{activity_description}")
                    if item.get("note"):
                        lines.append(f"  - 備註：{item.get('note')}")
                elif item_type == "meal":
                    lines.append(f"- {time_text} {item.get('name', '午餐／休息')}")
                    lines.append("  - 活動說明：安排可用餐景點或附近餐點")

    lines.extend([
        "",
        "## 行程安排原因",
        ai_content.get("arrangement_reason") or _fallback_arrangement_reason(parsed_request, trip_context, itinerary_result),
        "",
        "## 路線合理性",
        ai_content.get("route_rationale") or _fallback_route_rationale(itinerary_result),
        "",
        "## 資料來源",
        "- 資料庫景點資料",
        "- 路線驗證結果",
        "- Gemini 內容整理",
    ])

    if warnings:
        lines.extend([
            "",
            "## 補充說明",
        ])
        for warning in warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines).strip()