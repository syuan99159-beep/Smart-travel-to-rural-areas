from datetime import datetime, timedelta

from models.spot_model import list_spots
from services.maps_service import get_travel_time


def _parse_time(value):
    return datetime.strptime(value, "%H:%M")


def _format_time(value):
    return value.strftime("%H:%M")


def _next_end_time(current_time, minutes):
    return current_time + timedelta(minutes=minutes)


def _select_spots(filters):
    search_filters = dict(filters)
    search_filters.pop("itinerary_length", None)
    search_filters.pop("start_time", None)
    search_filters.pop("end_time", None)
    search_filters.pop("origin", None)
    search_filters["limit"] = 10
    return list_spots(search_filters)


def generate_itinerary(filters):
    start_time = _parse_time(filters.get("start_time", "09:00"))
    end_time = _parse_time(filters.get("end_time", "17:00"))
    itinerary_length = filters.get("itinerary_length", "full_day")
    available_minutes = int((end_time - start_time).total_seconds() // 60)

    spots = _select_spots(filters)
    if not spots:
        return {
            "status": "empty",
            "message": "找不到符合條件的景點。",
            "items": [],
            "is_rushed": False,
        }

    max_spots = 3 if itinerary_length == "half_day" else 5
    selected_spots = spots[:max_spots]

    current_time = start_time
    items = []
    total_travel_minutes = 0
    total_stay_minutes = 0
    lunch_added = False
    rush_reasons = []

    previous_spot = None
    has_meal_candidate = any(spot["can_eat"] == 1 for spot in selected_spots)

    for spot in selected_spots:
        travel_minutes = 0
        if previous_spot is not None:
            travel_info = get_travel_time(previous_spot, spot)
            travel_minutes = int(travel_info.get("travel_minutes") or 0)
        elif filters.get("origin_latitude") and filters.get("origin_longitude"):
            origin = {
                "latitude": filters["origin_latitude"],
                "longitude": filters["origin_longitude"],
            }
            travel_info = get_travel_time(origin, spot)
            travel_minutes = int(travel_info.get("travel_minutes") or 0)
        else:
            travel_minutes = 15

        travel_end = _next_end_time(current_time, travel_minutes)
        total_travel_minutes += travel_minutes
        current_time = travel_end

        if not lunch_added and has_meal_candidate:
            lunch_window_start = _parse_time("11:30")
            lunch_window_end = _parse_time("13:30")
            if current_time >= lunch_window_start and current_time <= lunch_window_end:
                lunch_start = current_time
                lunch_end = _next_end_time(lunch_start, 60)
                items.append(
                    {
                        "item_type": "meal",
                        "title": "午餐時間",
                        "start_time": _format_time(lunch_start),
                        "end_time": _format_time(lunch_end),
                        "stay_minutes": 60,
                        "travel_minutes": 0,
                        "meal_type": "午餐",
                        "notes": "依可用餐景點與時間窗安排。",
                    }
                )
                total_stay_minutes += 60
                current_time = lunch_end
                lunch_added = True

        stay_minutes = int(spot["recommended_stay_minutes"])
        stay_end = _next_end_time(current_time, stay_minutes)
        if stay_end > end_time:
            rush_reasons.append(f"{spot['name']} 的停留時間已超過可用時間。")
            break

        items.append(
            {
                "item_type": "spot",
                "spot_id": spot["id"],
                "title": spot["name"],
                "start_time": _format_time(current_time),
                "end_time": _format_time(stay_end),
                "stay_minutes": stay_minutes,
                "travel_minutes": travel_minutes,
                "meal_type": spot["meal_type"],
                "notes": f"{spot['region']}｜{spot['activity_type']}",
            }
        )
        total_stay_minutes += stay_minutes
        current_time = stay_end
        previous_spot = spot

    if current_time > end_time:
        rush_reasons.append("行程已超過結束時間。")

    remaining_minutes = int((end_time - current_time).total_seconds() // 60)
    if total_travel_minutes > available_minutes * 0.35:
        rush_reasons.append("車程占比偏高。")
    if remaining_minutes < 20:
        rush_reasons.append("預留緩衝時間不足。")
    if len(items) < 2:
        rush_reasons.append("行程站點數過少或條件過緊。")

    is_rushed = len(rush_reasons) > 0

    return {
        "status": "ok",
        "message": "已產生行程。",
        "items": items,
        "start_time": _format_time(start_time),
        "end_time": _format_time(end_time),
        "itinerary_length": itinerary_length,
        "total_travel_minutes": total_travel_minutes,
        "total_stay_minutes": total_stay_minutes,
        "is_rushed": is_rushed,
        "rush_reason": rush_reasons,
    }

