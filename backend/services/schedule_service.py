from datetime import datetime, timedelta
import json
import logging

from db import get_db
from services.gemini_service import generate_text
from services.maps_service import get_travel_time


DEFAULT_WINDOWS = {
    "半日": ("09:00", "13:00"),
    "一日": ("09:00", "17:00"),
}

LUNCH_START = "11:30"
LUNCH_END = "13:30"
LUNCH_MINUTES = 60
MIN_SPOT_COUNT_WARNING = 2
MAX_SPOTS_BY_TRIP = {
    "半日": 3,
    "一日": 5,
}


logger = logging.getLogger(__name__)


def _parse_time(value):
    return datetime.strptime(value, "%H:%M")


def _format_time(value):
    return value.strftime("%H:%M")


def _normalize_trip_length(value):
    if value in ("half_day", "半日"):
        return "半日"
    return "一日"


def _derive_trip_duration_label(start_dt, end_dt):
    duration = end_dt - start_dt
    total_hours = duration.total_seconds() / 3600.0

    if total_hours <= 6:
        return "半日"
    if total_hours <= 24:
        return "一日"

    total_days = max(2, duration.days + (1 if duration.seconds > 0 else 0))
    if total_days == 2:
        return "二日一夜"
    if total_days == 3:
        return "三天兩夜"
    if total_days == 4:
        return "四天三夜"
    return f"{total_days}天行程"


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except Exception:
        return None


def _build_datetime(base_time, hhmm):
    parsed = _parse_time(hhmm)
    return base_time.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)


def _add_minutes(value, minutes):
    return value + timedelta(minutes=minutes)


def _is_truthy(value):
    return value in (1, True, "1", "true", "True")


def _candidate_filters(payload):
    trip_length = payload.get("trip_length") or payload.get("duration")
    if trip_length in ("", "all", None):
        trip_length = None
    if trip_length in ("full_day", "一日"):
        trip_length = "一日"
    elif trip_length in ("half_day", "半日"):
        trip_length = "半日"

    return {
        "area": payload.get("area") or payload.get("region"),
        "type": payload.get("type") or payload.get("category") or payload.get("activity_type"),
        "trip_length": trip_length,
        "stay_type": payload.get("stay_type") or payload.get("stay_level"),
        "indoor_outdoor": payload.get("indoor_outdoor") or payload.get("space"),
        "budget": payload.get("budget") or payload.get("budget_level"),
        "keyword": payload.get("keyword") or payload.get("search"),
        "exclude_keywords": payload.get("exclude_keywords") or [],
        "limit": int(payload.get("limit") or 30),
    }


def _normalize_exclude_keywords(value):
    if not value:
        return []
    if isinstance(value, str):
        raw_values = [value]
    else:
        raw_values = list(value)

    keywords = []
    for raw_value in raw_values:
        for part in str(raw_value).replace("，", ",").replace("、", ",").split(","):
            text = part.strip()
            if text and text not in keywords:
                keywords.append(text)
    return keywords


def _normalize_keyword(keyword):
    if keyword is None:
        return ""

    if isinstance(keyword, list):
        keyword = " ".join(
            str(item).strip()
            for item in keyword
            if str(item).strip()
        )

    return str(keyword).strip()


def _select_spots(payload):
    filters = _candidate_filters(payload)
    clauses = ["is_active = 1"]
    params = []

    keyword = filters.get("keyword")
    normalized_keyword = _normalize_keyword(keyword)
    print("[schedule] keyword =", keyword)
    print("[schedule] normalized keyword =", normalized_keyword)

    area = filters.get("area")
    if area:
        clauses.append("area LIKE ?")
        params.append(f"%{area}%")

    parent_type = filters.get("type")
    if parent_type == "親子":
        clauses.append("(category LIKE ? OR keywords LIKE ? OR category LIKE ? OR keywords LIKE ? OR category LIKE ? OR keywords LIKE ? OR category LIKE ? OR keywords LIKE ? OR category LIKE ? OR keywords LIKE ?)")
        params.extend([
            "%親子%", "%親子%",
            "%DIY%", "%DIY%",
            "%農場%", "%農場%",
            "%生態%", "%生態%",
            "%手作%", "%手作%",
        ])
    elif parent_type:
        clauses.append("(category LIKE ? OR keywords LIKE ?)")
        params.extend([f"%{parent_type}%", f"%{parent_type}%"])

    if filters.get("trip_length"):
        clauses.append("trip_length = ?")
        params.append(filters["trip_length"])

    if filters.get("stay_type"):
        clauses.append("stay_type = ?")
        params.append(filters["stay_type"])

    if filters.get("indoor_outdoor"):
        clauses.append("indoor_outdoor = ?")
        params.append(filters["indoor_outdoor"])

    if filters.get("budget"):
        clauses.append("budget = ?")
        params.append(filters["budget"])

    if normalized_keyword:
        clauses.append("(name LIKE ? OR category LIKE ? OR description LIKE ? OR keywords LIKE ?)")
        keyword_value = f"%{normalized_keyword}%"
        params.extend([keyword_value, keyword_value, keyword_value, keyword_value])

    for exclude_keyword in _normalize_exclude_keywords(filters.get("exclude_keywords")):
        clauses.append("NOT (name LIKE ? OR keywords LIKE ? OR description LIKE ?)")
        exclude_value = f"%{exclude_keyword}%"
        params.extend([exclude_value, exclude_value, exclude_value])

    where_sql = " AND ".join(clauses)
    limit_sql = ""
    if filters.get("limit"):
        limit_sql = " LIMIT ?"
        params.append(int(filters["limit"]))

    sql = f"""
        SELECT
            id,
            name,
            area,
            address,
            latitude,
            longitude,
            category,
            trip_length,
            stay_type,
            stay_minutes,
            budget,
            indoor_outdoor,
            can_dine,
            meal_type,
            description,
            image,
            keywords,
            area AS region,
            category AS activity_type,
            trip_length AS duration,
            stay_type AS stay_level,
            stay_minutes AS recommended_stay_minutes,
            budget AS budget_level,
            can_dine AS can_eat
        FROM spots
        WHERE {where_sql}
        ORDER BY area, name
        {limit_sql}
    """
    db = get_db()
    rows = db.execute(sql, params).fetchall()
    print("[schedule] received filters =", filters)
    print("[schedule] SQL =", sql.strip())
    print("[schedule] params =", params)
    print("[schedule] count =", len(rows))
    print("[schedule] selected spots =", [row["name"] for row in rows[:10]])
    print("[schedule] first rows =", [
        {
            "name": row["name"],
            "area": row["area"],
            "category": row["category"],
            "trip_length": row["trip_length"],
        }
        for row in rows[:5]
    ])
    return [dict(row) for row in rows]


def _build_candidate_layers(payload):
    base_payload = dict(payload)
    area = base_payload.get("area") or base_payload.get("region")
    category = base_payload.get("category") or base_payload.get("activity_type")
    trip_length = base_payload.get("trip_length") or base_payload.get("duration")

    layers = [
        {"name": "exact", "payload": dict(base_payload)},
        {"name": "relax_category", "payload": {**base_payload, "category": None, "activity_type": None}},
        {"name": "relax_duration", "payload": {**base_payload, "trip_length": None, "duration": None}},
        {"name": "area_only", "payload": {**base_payload, "category": None, "activity_type": None, "trip_length": None, "duration": None}},
    ]

    # Preserve the original request context for logging.
    return {
        "area": area,
        "category": category,
        "trip_length": trip_length,
        "layers": layers,
    }


def _select_spots_relaxed(payload):
    relaxed_payload = dict(payload)
    relaxed_payload.pop("trip_length", None)
    relaxed_payload.pop("duration", None)
    return _select_spots(relaxed_payload)


def _default_window(trip_length):
    return DEFAULT_WINDOWS.get(trip_length, DEFAULT_WINDOWS["一日"])


def _count_spot_items(items):
    return sum(1 for item in items if item["type"] == "spot")


def _find_lunch_anchor_index(spots):
    for index, spot in enumerate(spots):
        if _is_truthy(spot.get("can_dine")):
            return index
    return 0


def _make_spot_item(spot, start_time, end_time, travel_minutes, travel_info=None):
    stay_minutes = int(spot.get("stay_minutes") or spot.get("recommended_stay_minutes") or 0)
    travel_note = None
    if travel_info:
        if travel_info.get("source") == "same_place":
            travel_note = "兩個活動地點相近，可輕鬆步行前往"
        elif travel_info.get("source") == "fallback_maps":
            travel_note = "目前使用系統估算車程"
        elif travel_info.get("warning"):
            travel_note = travel_info.get("warning")
        elif travel_info.get("duration_text"):
            travel_note = f"Google Maps 驗證車程：約 {travel_info.get('duration_text')}"
    return {
        "type": "spot",
        "spot_id": spot.get("id"),
        "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
        "name": spot.get("name", "未知景點"),
        "stay_minutes": stay_minutes,
        "travel_minutes": travel_minutes,
        "note": f"建議停留 {stay_minutes} 分鐘",
        "travel_note": travel_note,
        "source": travel_info.get("source") if travel_info else None,
        "distance_text": travel_info.get("distance_text") if travel_info else None,
        "duration_text": travel_info.get("duration_text") if travel_info else None,
    }


def _make_meal_item(start_time, travel_minutes, travel_info=None):
    end_time = _add_minutes(start_time, LUNCH_MINUTES)
    return {
        "type": "meal",
        "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
        "name": "午餐時間",
        "stay_minutes": LUNCH_MINUTES,
        "travel_minutes": travel_minutes,
        "note": "安排可用餐景點或附近餐點",
        "source": travel_info.get("source") if travel_info else None,
        "distance_text": travel_info.get("distance_text") if travel_info else None,
        "duration_text": travel_info.get("duration_text") if travel_info else None,
    }


def _resolve_origin(payload, start_point):
    lat = payload.get("origin_latitude")
    lng = payload.get("origin_longitude")
    if lat in (None, "") or lng in (None, ""):
        if not start_point:
            return None
        return {"name": start_point}
    try:
        return {"latitude": float(lat), "longitude": float(lng), "name": start_point}
    except Exception:
        if not start_point:
            return None
        return {"name": start_point}


def _resolve_time_window(payload, trip_length):
    default_start, default_end = _default_window(trip_length)

    def _safe_parse_time(value):
        try:
            if not value:
                return None
            return _parse_time(value)
        except Exception:
            return None

    start_dt = _parse_datetime(payload.get("start_datetime"))
    end_dt = _parse_datetime(payload.get("end_datetime"))

    if not start_dt:
        start_date = payload.get("start_date") or payload.get("date")
        start_time_value = payload.get("start_time") or default_start
        if start_date and start_time_value:
            start_dt = _parse_datetime(f"{start_date} {start_time_value}")

    if start_dt and end_dt:
        return start_dt, end_dt

    if start_dt and not end_dt:
        end_date = payload.get("end_date")
        end_time_value = payload.get("end_time")
        if end_date and end_time_value:
            end_dt = _parse_datetime(f"{end_date} {end_time_value}")

        if not end_dt:
            end_dt = start_dt + timedelta(days=1)

        return start_dt, end_dt

    if not start_dt and not end_dt:
        start_date = payload.get("start_date") or payload.get("date")
        start_time_value = payload.get("start_time") or default_start
        end_date = payload.get("end_date")
        end_time_value = payload.get("end_time")

        if start_date and start_time_value:
            start_dt = _parse_datetime(f"{start_date} {start_time_value}")
        if start_dt and end_date and end_time_value:
            end_dt = _parse_datetime(f"{end_date} {end_time_value}")

        if start_dt and not end_dt:
            end_dt = start_dt + timedelta(days=1)

        if start_dt and end_dt:
            return start_dt, end_dt

    start_time_value = payload.get("start_time") or default_start
    end_time_value = payload.get("end_time") or default_end
    start_time = _safe_parse_time(start_time_value) or _parse_time(default_start)
    end_time = _safe_parse_time(end_time_value) or _parse_time(default_end)
    today = datetime.now()
    start_dt = today.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
    end_dt = today.replace(hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0)
    return start_dt, end_dt


def _attempt_schedule(spots, trip_length, start_dt, end_dt, origin):
    items = []
    warnings = []
    warning_set = set()
    total_stay_minutes = 0
    total_travel_minutes = 0
    total_meal_minutes = 0

    days = (end_dt.date() - start_dt.date()).days + 1
    max_spots_per_day = MAX_SPOTS_BY_TRIP.get(trip_length, 5)
    previous_spot_global = None
    scheduled_ids = set()
    unique_candidate_ids = {spot.get("id") for spot in spots if spot.get("id") is not None}

    for day_idx in range(days):
        day_date = start_dt.date() + timedelta(days=day_idx)
        day_start = start_dt if day_idx == 0 else datetime.combine(day_date, start_dt.time())
        day_end = end_dt if day_idx == days - 1 else datetime.combine(day_date, end_dt.time())

        current_time = day_start
        previous_spot = previous_spot_global
        lunch_added = trip_length != "一日"
        day_count = 0
        day_lunch_start = _build_datetime(day_start, LUNCH_START)
        day_lunch_end = _build_datetime(day_start, LUNCH_END)
        remaining_days = days - day_idx
        remaining_candidates = max(0, len(unique_candidate_ids - scheduled_ids))
        day_target = min(
            max_spots_per_day,
            max(1, (remaining_candidates + remaining_days - 1) // remaining_days),
        )

        for spot in spots:
            if day_count >= day_target:
                break
            sid = spot.get("id")
            if sid in scheduled_ids:
                continue

            if previous_spot is None:
                if origin is None:
                    travel_info = {
                        "travel_minutes": 0,
                        "source": "originless",
                        "warning": "未提供出發地，僅安排景點內行程，不計算出發車程。",
                    }
                    travel_minutes = 0
                else:
                    travel_info = get_travel_time(origin, spot)
                    travel_minutes = int(travel_info.get("travel_minutes") or 30)
            else:
                travel_info = get_travel_time(previous_spot, spot)
                travel_minutes = int(travel_info.get("travel_minutes") or 15)

            warning = travel_info.get("warning")
            if warning and warning not in warning_set:
                warnings.append(warning)
                warning_set.add(warning)

            spot_start = _add_minutes(current_time, travel_minutes)
            if spot_start >= day_end:
                continue

            if trip_length == "一日" and not lunch_added and day_lunch_start <= spot_start <= day_lunch_end:
                meal_end = _add_minutes(spot_start, LUNCH_MINUTES)
                if meal_end > day_end:
                    continue
                items.append(_make_meal_item(spot_start, 0, travel_info=travel_info))
                total_meal_minutes += LUNCH_MINUTES
                current_time = meal_end
                lunch_added = True
                spot_start = _add_minutes(current_time, travel_minutes)
                if spot_start >= day_end:
                    continue

            stay_minutes = int(spot.get("stay_minutes") or spot.get("recommended_stay_minutes") or 0)
            spot_end = _add_minutes(spot_start, stay_minutes)
            if spot_end > day_end:
                continue

            items.append(_make_spot_item(spot, spot_start, spot_end, travel_minutes, travel_info=travel_info))
            total_travel_minutes += travel_minutes
            total_stay_minutes += stay_minutes
            current_time = spot_end
            previous_spot = spot
            previous_spot_global = spot
            scheduled_ids.add(sid)
            day_count += 1

        if trip_length == "一日" and not lunch_added:
            meal_start = current_time if current_time >= day_lunch_start else day_lunch_start
            meal_end = _add_minutes(meal_start, LUNCH_MINUTES)
            if meal_end <= day_end:
                items.append(_make_meal_item(meal_start, 0))
                total_meal_minutes += LUNCH_MINUTES

        if day_count == 0:
            warnings.append(f"第 {day_idx + 1} 日無可排入之景點")

    if not items:
        return {
            "success": False,
            "message": "條件太嚴格，景點不足或時間不足。",
            "warnings": warnings + ["條件太嚴格，景點不足"],
        }

    scheduled_spot_count = _count_spot_items(items)
    if scheduled_spot_count < MIN_SPOT_COUNT_WARNING:
        warnings.append(f"景點數量不足，僅排出 {scheduled_spot_count} 個景點")

    if total_travel_minutes > 120 * max(days, 1):
        warnings.append("行程可能過趕")

    return {
        "success": True,
        "warnings": warnings,
        "items": items,
        "total_stay_minutes": total_stay_minutes,
        "total_travel_minutes": total_travel_minutes,
        "total_meal_minutes": total_meal_minutes,
        "is_too_rushed": total_travel_minutes > 120 * max(days, 1),
    }


def _clean_json_text(text):
    if not text:
        return ""
    stripped = str(text).strip()
    if stripped.startswith("```"):
        stripped = stripped.replace("```json", "", 1).replace("```", "")
    return stripped.strip()


def _extract_json_payload(text):
    cleaned = _clean_json_text(text)
    if not cleaned:
        return None
    try:
        return json.loads(cleaned)
    except Exception:
        try:
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
        except Exception:
            return None
    return None


def _spot_candidate_payload(spot):
    return {
        "id": spot.get("id"),
        "name": spot.get("name"),
        "address": spot.get("address") or "",
        "category": spot.get("category") or "",
        "stay_minutes": int(spot.get("stay_minutes") or spot.get("recommended_stay_minutes") or 60),
        "meal_type": spot.get("meal_type") or "",
        "latitude": spot.get("latitude"),
        "longitude": spot.get("longitude"),
        "is_meal": int(spot.get("is_meal") or spot.get("can_eat") or spot.get("can_dine") or 0),
        "description": spot.get("description") or "",
        "area": spot.get("area") or spot.get("region") or "",
        "keywords": spot.get("keywords") or "",
    }


def _fetch_spots_by_ids(spot_ids):
    if not spot_ids:
        return []

    db = get_db()
    placeholders = ",".join(["?"] * len(spot_ids))
    rows = db.execute(
        f"""
        SELECT
            id,
            name,
            area,
            address,
            latitude,
            longitude,
            category,
            trip_length,
            stay_type,
            stay_minutes,
            budget,
            indoor_outdoor,
            can_dine,
            can_dine AS is_meal,
            meal_type,
            description,
            image,
            keywords,
            area AS region,
            category AS activity_type,
            trip_length AS duration,
            stay_type AS stay_level,
            stay_minutes AS recommended_stay_minutes,
            budget AS budget_level,
            can_dine AS can_eat
        FROM spots
        WHERE id IN ({placeholders})
        """,
        list(spot_ids),
    ).fetchall()

    spot_map = {row["id"]: _resolve_spot_image(dict(row)) for row in rows}
    ordered_spots = [spot_map[spot_id] for spot_id in spot_ids if spot_id in spot_map]
    return ordered_spots


def _build_selection_prompt(payload, candidates, start_dt, end_dt, trip_length, origin):
    prompt_payload = {
        "user_request": {
            "area": payload.get("area") or payload.get("region") or "",
            "category": payload.get("type") or payload.get("category") or payload.get("activity_type") or "",
            "trip_length": trip_length,
            "keyword": payload.get("keyword") or "",
            "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
            "origin": origin.get("name") if isinstance(origin, dict) else origin,
            "preferences": payload.get("preferences") or [],
            "exclude_keywords": payload.get("exclude_keywords") or [],
        },
        "available_spots": [_spot_candidate_payload(spot) for spot in candidates],
        "output_rules": {
            "must_only_use_available_spots": True,
            "must_not_invent_spots": True,
            "must_not_modify_fields": ["name", "address", "stay_minutes", "travel_time", "route_source"],
            "output_format": "JSON array only, e.g. [1, 5, 8, 12]",
        },
    }

    return "\n".join([
        "你是一個旅遊規劃助手。",
        "以下提供的是資料庫查詢出的景點。",
        "請根據：",
        "- 使用者偏好",
        "- 行程天數",
        "- 景點類型",
        "- 地理區域",
        "選出最適合的景點順序。",
        "只輸出 JSON：",
        "{",
        '  "selected_spots":[',
        '    {"spot_id":1},',
        '    {"spot_id":5},',
        '    {"spot_id":9}',
        "  ]",
        "}",
        "禁止：",
        "- 新增景點",
        "- 修改景點名稱",
        "- 修改地址",
        "- 修改停留時間",
        "- 修改資料庫內容",
        "如果沒有合適景點，請輸出 []",
        json.dumps(prompt_payload, ensure_ascii=False, indent=2),
    ])


def _extract_selected_spot_ids(text):
    parsed = _extract_json_payload(text)
    if isinstance(parsed, dict):
        if isinstance(parsed.get("selected_spot_ids"), list):
            parsed = parsed.get("selected_spot_ids")
        elif isinstance(parsed.get("selected_spots"), list):
            parsed = parsed.get("selected_spots")
        elif isinstance(parsed.get("spots"), list):
            parsed = parsed.get("spots")

    if not isinstance(parsed, list):
        return None

    selected_ids = []
    seen = set()
    for item in parsed:
        spot_id = None
        if isinstance(item, int):
            spot_id = item
        elif isinstance(item, str) and item.isdigit():
            spot_id = int(item)
        elif isinstance(item, dict):
            value = item.get("spot_id") or item.get("id")
            if isinstance(value, int):
                spot_id = value
            elif isinstance(value, str) and value.isdigit():
                spot_id = int(value)

        if spot_id is not None and spot_id not in seen:
            selected_ids.append(spot_id)
            seen.add(spot_id)

    return selected_ids


def _select_spot_ids_with_gemini(payload, candidates, start_dt, end_dt, trip_length, origin):
    if not candidates:
        return [], {"source": "gemini", "warning": "找不到符合條件的景點"}

    prompt = _build_selection_prompt(payload, candidates, start_dt, end_dt, trip_length, origin)
    result = generate_text(prompt, max_output_tokens=600, temperature=0.1)
    if not result.get("success") or not result.get("text"):
        return None, {"source": "gemini", "warning": "Gemini 選點失敗，無法產生行程"}

    selected_ids = _extract_selected_spot_ids(result.get("text"))
    if not selected_ids:
        return None, {"source": "gemini", "warning": "Gemini 未回傳有效 selected_spot_ids"}

    candidate_id_set = {spot.get("id") for spot in candidates if spot.get("id") is not None}
    filtered_ids = [spot_id for spot_id in selected_ids if spot_id in candidate_id_set]
    if not filtered_ids:
        return None, {"source": "gemini", "warning": "Gemini 回傳的 selected_spot_ids 不在候選清單中"}

    return filtered_ids, {"source": "gemini", "warning": None}


def _is_restaurant_spot(spot):
    text = " ".join([
        str(spot.get("name") or ""),
        str(spot.get("category") or ""),
        str(spot.get("meal_type") or ""),
        str(spot.get("description") or ""),
        str(spot.get("keywords") or ""),
    ])
    lowered = text.lower()
    return any(token in lowered for token in ("餐廳", "美食", "正餐", "lunch", "dinner"))


def _route_source_label(source):
    mapping = {
        "google_maps": "Google Maps",
        "fallback_maps": "系統估算",
        "same_place": "同一地點",
        "originless": "系統估算",
        "Google Maps": "Google Maps",
        "系統估算": "系統估算",
        "同一地點": "同一地點",
    }
    return mapping.get(source, source or "系統估算")


def _route_duration_text(travel_info):
    if not travel_info:
        return "目前使用系統估算車程"
    source = travel_info.get("source")
    if source == "google_maps":
        return travel_info.get("duration_text") or f"約 {int(travel_info.get('travel_minutes') or 0)} 分鐘"
    if source == "same_place":
        return "同一地點，無需移動"
    return "目前使用系統估算車程"


def _meal_label_for_time(dt_value):
    time_value = dt_value.time()
    lunch_start = datetime.strptime(LUNCH_START, "%H:%M").time()
    lunch_end = datetime.strptime(LUNCH_END, "%H:%M").time()
    dinner_start = datetime.strptime("17:00", "%H:%M").time()
    dinner_end = datetime.strptime("19:00", "%H:%M").time()

    if lunch_start <= time_value <= lunch_end:
        return "午餐／休息"
    if dinner_start <= time_value <= dinner_end:
        return "晚餐／休息"
    return None


def _make_spot_item_v2(spot, start_time, end_time, travel_minutes, travel_info=None, travel_from=None):
    travel_info = travel_info or {}
    source = _route_source_label(travel_info.get("source"))
    duration_text = _route_duration_text(travel_info)
    stay_minutes = int(spot.get("stay_minutes") or spot.get("recommended_stay_minutes") or 0)
    return {
        "type": "spot",
        "spot_id": spot.get("id"),
        "name": spot.get("name", "未知景點"),
        "address": spot.get("address") or "",
        "category": spot.get("category") or "",
        "latitude": spot.get("latitude"),
        "longitude": spot.get("longitude"),
        "meal_type": spot.get("meal_type") or "",
        "is_meal": int(spot.get("is_meal") or spot.get("can_eat") or spot.get("can_dine") or 0),
        "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
        "stay_minutes": stay_minutes,
        "travel_minutes": int(travel_minutes or 0),
        "travel_from": travel_from or "",
        "duration_text": duration_text,
        "source": source,
        "description": spot.get("description") or "",
        "note": f"建議停留 {stay_minutes} 分鐘",
    }


def _make_meal_item_v2(start_time, meal_minutes=60, meal_label="午餐／休息", travel_from=None):
    end_time = _add_minutes(start_time, meal_minutes)
    return {
        "type": "meal",
        "name": meal_label,
        "address": "",
        "category": "",
        "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
        "stay_minutes": meal_minutes,
        "travel_minutes": 0,
        "travel_from": travel_from or "",
        "duration_text": "目前使用系統估算車程",
        "source": "系統估算",
        "description": "當沒有合適餐廳時，於用餐時段安排休息。",
        "note": "安排可用餐景點或附近餐點",
    }


def _build_summary(trip_length, start_dt, end_dt, start_point, total_stay_minutes, total_travel_minutes, total_meal_minutes):
    duration_label = _derive_trip_duration_label(start_dt, end_dt)
    return {
        "trip_length": duration_label,
        "duration_label": duration_label,
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
        "total_stay_minutes": total_stay_minutes,
        "total_travel_minutes": total_travel_minutes,
        "total_meal_minutes": total_meal_minutes,
        "start_point": start_point,
    }


def _schedule_selected_spots(ordered_spots, trip_length, start_dt, end_dt, origin, start_point):
    items = []
    warnings = []
    warning_set = set()
    total_stay_minutes = 0
    total_travel_minutes = 0
    total_meal_minutes = 0

    if not ordered_spots:
        return {
            "success": False,
            "message": "找不到符合條件的景點。",
            "warnings": ["找不到符合條件的景點"],
            "items": [],
            "summary": _build_summary(trip_length, start_dt, end_dt, start_point, 0, 0, 0),
            "is_too_rushed": False,
        }

    days = (end_dt.date() - start_dt.date()).days + 1
    previous_spot_global = None
    spot_index = 0
    has_restaurant = any(_is_restaurant_spot(spot) for spot in ordered_spots)

    for day_idx in range(days):
        day_date = start_dt.date() + timedelta(days=day_idx)
        day_start = start_dt if day_idx == 0 else datetime.combine(day_date, start_dt.time())
        day_end = end_dt if day_idx == days - 1 else datetime.combine(day_date, end_dt.time())
        current_time = day_start
        previous_spot = previous_spot_global
        day_meals_added = set()
        day_spot_count = 0

        while spot_index < len(ordered_spots):
            spot = ordered_spots[spot_index]
            if previous_spot is None:
                travel_from = start_point or (origin.get("name") if isinstance(origin, dict) else origin) or "出發地"
                travel_origin = origin
            else:
                travel_from = previous_spot.get("name") or start_point or "前一站"
                travel_origin = previous_spot

            travel_info = get_travel_time(travel_origin, spot)
            warning = travel_info.get("warning")
            if warning and warning not in warning_set:
                warnings.append(warning)
                warning_set.add(warning)

            travel_minutes = int(travel_info.get("travel_minutes") or 0)
            spot_start = _add_minutes(current_time, travel_minutes)
            if spot_start >= day_end:
                break

            if not has_restaurant:
                meal_label = _meal_label_for_time(spot_start)
                if meal_label and meal_label not in day_meals_added:
                    meal_end = _add_minutes(spot_start, 60)
                    if meal_end <= day_end:
                        items.append(_make_meal_item_v2(spot_start, meal_minutes=60, meal_label=meal_label, travel_from=travel_from))
                        total_meal_minutes += 60
                        current_time = meal_end
                        day_meals_added.add(meal_label)
                        continue

            stay_minutes = int(spot.get("stay_minutes") or spot.get("recommended_stay_minutes") or 0)
            spot_end = _add_minutes(spot_start, stay_minutes)
            if spot_end > day_end:
                break

            items.append(_make_spot_item_v2(spot, spot_start, spot_end, travel_minutes, travel_info=travel_info, travel_from=travel_from))
            total_travel_minutes += travel_minutes
            total_stay_minutes += stay_minutes
            current_time = spot_end
            previous_spot = spot
            previous_spot_global = spot
            spot_index += 1
            day_spot_count += 1

        if day_spot_count == 0 and spot_index >= len(ordered_spots):
            break

        if day_spot_count == 0:
            warnings.append(f"第 {day_idx + 1} 日無可排入之景點")

    if not items:
        return {
            "success": False,
            "message": "條件太嚴格，景點不足或時間不足。",
            "warnings": warnings + ["條件太嚴格，景點不足"],
            "items": [],
            "summary": _build_summary(trip_length, start_dt, end_dt, start_point, 0, 0, 0),
            "is_too_rushed": False,
        }

    scheduled_spot_count = sum(1 for item in items if item.get("type") == "spot")
    if scheduled_spot_count < MIN_SPOT_COUNT_WARNING:
        warnings.append(f"景點數量不足，僅排出 {scheduled_spot_count} 個景點")

    is_too_rushed = total_travel_minutes > 120 * max(days, 1)
    if is_too_rushed:
        warnings.append("行程可能過趕")

    summary = _build_summary(trip_length, start_dt, end_dt, start_point, total_stay_minutes, total_travel_minutes, total_meal_minutes)
    return {
        "success": True,
        "warnings": warnings,
        "items": items,
        "summary": summary,
        "is_too_rushed": is_too_rushed,
    }


def generate_itinerary(payload):
    trip_length = _normalize_trip_length(payload.get("trip_length") or payload.get("itinerary_length"))
    start_point_value = payload.get("start_point") or payload.get("origin")
    start_point = start_point_value.strip() if isinstance(start_point_value, str) and start_point_value.strip() else None
    origin = _resolve_origin(payload, start_point)
    logger.info("[schedule] received payload = %s", payload)
    logger.info("[schedule] selected area = %s", payload.get("area") or payload.get("region"))

    start_dt, end_dt = _resolve_time_window(payload, trip_length)

    if end_dt <= start_dt:
        return {
            "success": False,
            "message": "結束時間必須晚於開始時間。",
            "warnings": [],
            "is_too_rushed": False,
            "summary": _build_summary(trip_length, start_dt, end_dt, start_point, 0, 0, 0),
            "items": [],
        }

    days = (end_dt.date() - start_dt.date()).days + 1
    per_day_max = MAX_SPOTS_BY_TRIP.get(trip_length, 5)
    search_payload = {**payload, "limit": max(per_day_max * days * 3, 20)}

    candidate_plan = _build_candidate_layers(search_payload)
    layer_counts = []
    candidates = []
    chosen_layer = None

    logger.info(
        "schedule_service candidate search original=%s",
        {
            "area": candidate_plan["area"],
            "category": candidate_plan["category"],
            "trip_length": candidate_plan["trip_length"],
            "limit": search_payload.get("limit"),
        },
    )

    for layer in candidate_plan["layers"]:
        layer_candidates = _select_spots(layer["payload"])
        layer_count = len(layer_candidates)
        layer_counts.append((layer["name"], layer_count))
        logger.info("schedule_service candidate search layer=%s count=%s", layer["name"], layer_count)
        if layer_count >= 2 and not candidates:
            candidates = layer_candidates
            chosen_layer = layer["name"]

    if not candidates:
        for layer in reversed(candidate_plan["layers"]):
            layer_candidates = _select_spots(layer["payload"])
            if layer_candidates:
                candidates = layer_candidates
                chosen_layer = layer["name"]
                break

    logger.info(
        "schedule_service candidate search selected=%s count=%s layer_counts=%s",
        chosen_layer,
        len(candidates),
        layer_counts,
    )

    if not candidates:
        return {
            "success": False,
            "message": "找不到符合條件的景點。",
            "warnings": ["找不到符合條件的景點"],
            "is_too_rushed": False,
            "summary": _build_summary(trip_length, start_dt, end_dt, start_point, 0, 0, 0),
            "items": [],
        }

    selected_spot_ids, selection_meta = _select_spot_ids_with_gemini(payload, candidates, start_dt, end_dt, trip_length, origin)
    if not selected_spot_ids:
        return {
            "success": False,
            "message": selection_meta.get("warning") or "Gemini 選點失敗",
            "is_too_rushed": False,
            "summary": _build_summary(trip_length, start_dt, end_dt, start_point, 0, 0, 0),
            "items": [],
            "warnings": [selection_meta.get("warning") or "Gemini 選點失敗"],
            "selected_layer": chosen_layer,
            "selected_by": selection_meta.get("source"),
        }

    selected_spots = _fetch_spots_by_ids(selected_spot_ids)
    if not selected_spots:
        return {
            "success": False,
            "message": "無法依 Gemini 選點重建景點資料。",
            "is_too_rushed": False,
            "summary": _build_summary(trip_length, start_dt, end_dt, start_point, 0, 0, 0),
            "items": [],
            "warnings": ["無法依 Gemini 選點重建景點資料"],
            "selected_layer": chosen_layer,
            "selected_by": selection_meta.get("source"),
        }

    schedule_result = _schedule_selected_spots(selected_spots, trip_length, start_dt, end_dt, origin, start_point)

    warnings = list(schedule_result.get("warnings") or [])
    if selection_meta.get("warning"):
        warnings.insert(0, selection_meta["warning"])
    if chosen_layer and chosen_layer != "exact":
        warnings.insert(0, f"已自動放寬篩選條件：{chosen_layer}")

    return {
        "success": bool(schedule_result.get("success")),
        "message": schedule_result.get("message") or ("行程產生成功" if schedule_result.get("success") else "行程產生失敗"),
        "is_too_rushed": schedule_result.get("is_too_rushed", False),
        "selected_layer": chosen_layer,
        "selected_by": selection_meta.get("source"),
        "warnings": warnings,
        "summary": schedule_result.get("summary") or _build_summary(trip_length, start_dt, end_dt, start_point, 0, 0, 0),
        "items": schedule_result.get("items") or [],
    }
