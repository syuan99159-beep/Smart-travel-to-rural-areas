from datetime import datetime, timedelta

from models.spot_model import list_spots
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


def _parse_time(value):
    return datetime.strptime(value, "%H:%M")


def _format_time(value):
    return value.strftime("%H:%M")


def _normalize_trip_length(value):
    if value in ("half_day", "半日"):
        return "半日"
    return "一日"


def _build_datetime(base_time, hhmm):
    parsed = _parse_time(hhmm)
    return base_time.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)


def _add_minutes(value, minutes):
    return value + timedelta(minutes=minutes)


def _is_truthy(value):
    return value in (1, True, "1", "true", "True")


def _candidate_filters(payload):
    return {
        "area": payload.get("area") or payload.get("region"),
        "category": payload.get("category") or payload.get("activity_type"),
        "trip_length": payload.get("trip_length") or payload.get("itinerary_length") or payload.get("duration"),
        "stay_type": payload.get("stay_type") or payload.get("stay_level"),
        "indoor_outdoor": payload.get("indoor_outdoor") or payload.get("space"),
        "budget": payload.get("budget") or payload.get("budget_level"),
        "keyword": payload.get("keyword") or payload.get("search"),
        "limit": 20,
    }


def _select_spots(payload):
    filters = _candidate_filters(payload)
    return list_spots(filters)


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
    return {
        "type": "spot",
        "spot_id": spot.get("id"),
        "start_time": _format_time(start_time),
        "end_time": _format_time(end_time),
        "name": spot.get("name", "未知景點"),
        "stay_minutes": stay_minutes,
        "travel_minutes": travel_minutes,
        "note": f"建議停留 {stay_minutes} 分鐘",
        "source": travel_info.get("source") if travel_info else None,
        "distance_text": travel_info.get("distance_text") if travel_info else None,
        "duration_text": travel_info.get("duration_text") if travel_info else None,
    }


def _make_meal_item(start_time, travel_minutes, travel_info=None):
    end_time = _add_minutes(start_time, LUNCH_MINUTES)
    return {
        "type": "meal",
        "start_time": _format_time(start_time),
        "end_time": _format_time(end_time),
        "name": "午餐時間",
        "stay_minutes": LUNCH_MINUTES,
        "travel_minutes": travel_minutes,
        "note": "安排可用餐景點或附近餐點",
        "source": travel_info.get("source") if travel_info else None,
        "distance_text": travel_info.get("distance_text") if travel_info else None,
        "duration_text": travel_info.get("duration_text") if travel_info else None,
    }


def _attempt_schedule(spots, trip_length, start_time, end_time, start_point):
    items = []
    warnings = []
    total_stay_minutes = 0
    total_travel_minutes = 0
    total_meal_minutes = 0

    current_time = start_time
    previous_spot = None
    lunch_added = trip_length != "一日"
    lunch_start_time = _build_datetime(start_time, LUNCH_START)
    lunch_end_time = _build_datetime(start_time, LUNCH_END)
    lunch_anchor_index = _find_lunch_anchor_index(spots) if trip_length == "一日" else -1

    for index, spot in enumerate(spots):
        if trip_length == "一日" and not lunch_added and current_time >= lunch_start_time:
            meal_start = current_time
            meal_end = _add_minutes(meal_start, LUNCH_MINUTES)

            if meal_end > end_time:
                return {
                    "success": False,
                    "message": "午餐安排後超過可用時間。",
                    "warnings": warnings + ["已自動減少景點數量"],
                }

            meal_travel_minutes = 10 if previous_spot and _is_truthy(previous_spot.get("can_dine")) else 15
            items.append(_make_meal_item(meal_start, meal_travel_minutes, travel_info=travel_info))
            total_travel_minutes += meal_travel_minutes
            total_meal_minutes += LUNCH_MINUTES
            current_time = meal_end
            lunch_added = True

        if previous_spot is None:
            travel_info = get_travel_time({"name": start_point}, spot)
            travel_minutes = int(travel_info.get("travel_minutes") or 30)
            if travel_info.get("warning"):
                warnings.append(travel_info.get("warning"))
        else:
            travel_info = get_travel_time(previous_spot, spot)
            travel_minutes = int(travel_info.get("travel_minutes") or 15)
            if travel_info.get("warning"):
                warnings.append(travel_info.get("warning"))

        spot_start = _add_minutes(current_time, travel_minutes)
        stay_minutes = int(spot.get("stay_minutes") or spot.get("recommended_stay_minutes") or 0)
        spot_end = _add_minutes(spot_start, stay_minutes)

        if spot_end > end_time:
            return {
                "success": False,
                "message": "已自動減少景點數量後仍超過結束時間。",
                "warnings": warnings + ["已自動減少景點數量"],
            }

        items.append(_make_spot_item(spot, spot_start, spot_end, travel_minutes, travel_info=travel_info))
        total_travel_minutes += travel_minutes
        total_stay_minutes += stay_minutes
        current_time = spot_end
        previous_spot = spot

        should_add_lunch = (
            trip_length == "一日"
            and not lunch_added
            and (index == lunch_anchor_index or index == len(spots) - 1)
        )
        if should_add_lunch:
            meal_start = current_time if current_time >= lunch_start_time else lunch_start_time
            meal_end = _add_minutes(meal_start, LUNCH_MINUTES)

            if meal_end > end_time:
                return {
                    "success": False,
                    "message": "午餐安排後超過可用時間。",
                    "warnings": warnings + ["已自動減少景點數量"],
                }

            meal_travel_minutes = 10 if _is_truthy(spot.get("can_dine")) else 15
            items.append(_make_meal_item(meal_start, meal_travel_minutes, travel_info=travel_info))
            total_travel_minutes += meal_travel_minutes
            total_meal_minutes += LUNCH_MINUTES
            current_time = meal_end
            lunch_added = True

    if trip_length == "一日" and not lunch_added:
        meal_start = current_time if current_time >= lunch_start_time else lunch_start_time
        meal_end = _add_minutes(meal_start, LUNCH_MINUTES)

        if meal_end > end_time:
            return {
                "success": False,
                "message": "午餐安排後超過可用時間。",
                "warnings": warnings + ["已自動減少景點數量"],
            }

        meal_travel_minutes = 10 if previous_spot and _is_truthy(previous_spot.get("can_dine")) else 15
        items.append(_make_meal_item(meal_start, meal_travel_minutes, travel_info=travel_info))
        total_travel_minutes += meal_travel_minutes
        total_meal_minutes += LUNCH_MINUTES
        current_time = meal_end

    if current_time > end_time:
        return {
            "success": False,
            "message": "行程仍超過結束時間。",
            "warnings": warnings + ["已自動減少景點數量"],
        }

    scheduled_spot_count = _count_spot_items(items)
    if scheduled_spot_count < MIN_SPOT_COUNT_WARNING:
        warnings.append(f"景點數量不足，僅排出 {scheduled_spot_count} 個景點")

    if total_travel_minutes > 120:
        warnings.append("行程可能過趕")

    return {
        "success": True,
        "warnings": warnings,
        "items": items,
        "total_stay_minutes": total_stay_minutes,
        "total_travel_minutes": total_travel_minutes,
        "total_meal_minutes": total_meal_minutes,
        "is_too_rushed": total_travel_minutes > 120,
        "start_point": start_point,
    }


def generate_itinerary(payload):
    trip_length = _normalize_trip_length(payload.get("trip_length") or payload.get("itinerary_length"))
    default_start, default_end = _default_window(trip_length)
    start_time_value = payload.get("start_time") or default_start
    end_time_value = payload.get("end_time") or default_end
    start_point = (payload.get("start_point") or payload.get("origin") or "南投車站").strip() or "南投車站"

    start_time = _parse_time(start_time_value)
    end_time = _parse_time(end_time_value)

    if end_time <= start_time:
        return {
            "success": False,
            "message": "結束時間必須晚於開始時間。",
            "warnings": [],
            "is_too_rushed": False,
            "summary": {
                "trip_length": trip_length,
                "start_time": _format_time(start_time),
                "end_time": _format_time(end_time),
                "total_stay_minutes": 0,
                "total_travel_minutes": 0,
                "total_meal_minutes": 0,
            },
            "items": [],
        }

    candidates = _select_spots(payload)
    if not candidates:
        return {
            "success": False,
            "message": "條件太嚴格，景點不足。",
            "warnings": ["條件太嚴格，景點不足"],
            "is_too_rushed": False,
            "summary": {
                "trip_length": trip_length,
                "start_time": _format_time(start_time),
                "end_time": _format_time(end_time),
                "total_stay_minutes": 0,
                "total_travel_minutes": 0,
                "total_meal_minutes": 0,
            },
            "items": [],
        }

    max_spots = MAX_SPOTS_BY_TRIP.get(trip_length, 5)
    selected_count = min(max_spots, len(candidates))
    last_error_message = ""
    auto_reduced = False

    for count in range(selected_count, 0, -1):
        attempt = _attempt_schedule(
            candidates[:count],
            trip_length,
            start_time,
            end_time,
            start_point,
        )

        if attempt["success"]:
            warnings = list(attempt["warnings"])
            if count < selected_count:
                warnings.insert(0, "已自動減少景點數量")
                auto_reduced = True

            if trip_length == "一日" and attempt["total_meal_minutes"] < LUNCH_MINUTES:
                warnings.append("一日遊已自動安排午餐")

            return {
                "success": True,
                "message": "行程產生成功",
                "is_too_rushed": attempt["is_too_rushed"],
                "warnings": warnings,
                "summary": {
                    "trip_length": trip_length,
                    "start_time": _format_time(start_time),
                    "end_time": _format_time(end_time),
                    "total_stay_minutes": attempt["total_stay_minutes"],
                    "total_travel_minutes": attempt["total_travel_minutes"],
                    "total_meal_minutes": attempt["total_meal_minutes"],
                    "start_point": start_point,
                },
                "items": attempt["items"],
            }

        last_error_message = attempt.get("message", "行程產生失敗。")
        if count < selected_count:
            auto_reduced = True

    final_warnings = ["條件太嚴格，景點不足"]
    if auto_reduced:
        final_warnings.insert(0, "已自動減少景點數量")
    if last_error_message:
        final_warnings.append(last_error_message)

    return {
        "success": False,
        "message": "行程產生失敗",
        "is_too_rushed": False,
        "warnings": final_warnings,
        "summary": {
            "trip_length": trip_length,
            "start_time": _format_time(start_time),
            "end_time": _format_time(end_time),
            "total_stay_minutes": 0,
            "total_travel_minutes": 0,
            "total_meal_minutes": 0,
            "start_point": start_point,
        },
        "items": [],
    }
