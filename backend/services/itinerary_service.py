from datetime import datetime, date, time as dt_time, timedelta

from models.spot_model import list_spots
from services.maps_service import get_travel_time


def _parse_datetime(value):
    """
    Parse a datetime string in format 'YYYY-MM-DD HH:MM' into a datetime object.
    If value is None or invalid, return today's date with 09:00 as default.
    """
    if not value:
        today = datetime.now()
        return datetime(today.year, today.month, today.day, 9, 0)
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except Exception:
        # fallback: try parse time-only HH:MM on today's date
        try:
            t = datetime.strptime(value, "%H:%M")
            today = datetime.now()
            return datetime(today.year, today.month, today.day, t.hour, t.minute)
        except Exception:
            today = datetime.now()
            return datetime(today.year, today.month, today.day, 9, 0)


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
    # allow caller to override limit
    limit = search_filters.pop("limit", 10)
    search_filters["limit"] = limit
    return list_spots(search_filters)


def generate_itinerary(filters):
    # accept either start_datetime/end_datetime (YYYY-MM-DD HH:MM) or legacy start_time/end_time
    start_dt = _parse_datetime(filters.get("start_datetime") or filters.get("start_time"))
    end_dt = _parse_datetime(filters.get("end_datetime") or filters.get("end_time"))
    itinerary_length = filters.get("itinerary_length", "full_day")

    # determine days span (inclusive)
    days = (end_dt.date() - start_dt.date()).days + 1

    max_spots_per_day = 3 if itinerary_length == "half_day" else 5

    # fetch a larger candidate pool for better fit (allow skipping long items)
    candidate_limit = max_spots_per_day * days * 3
    spots = _select_spots({**filters, "limit": candidate_limit})
    if not spots:
        return {
            "status": "empty",
            "message": "找不到符合條件的景點。",
            "items": [],
            "is_rushed": False,
        }

    items = []
    total_travel_minutes = 0
    total_stay_minutes = 0
    rush_reasons = []

    previous_spot_global = None
    scheduled_ids = set()

    # scan through candidate spots and assign to days, skipping ones that don't fit
    idx = 0
    n_candidates = len(spots)
    for day_idx in range(days):
        day_date = start_dt.date() + timedelta(days=day_idx)
        if day_idx == 0:
            day_start = start_dt
        else:
            day_start = datetime.combine(day_date, start_dt.time())

        if day_idx == days - 1:
            day_end = end_dt
        else:
            day_end = datetime.combine(day_date, end_dt.time())

        current_time = day_start
        previous_spot = previous_spot_global
        day_count = 0

        # try to fill up to max_spots_per_day by scanning candidates
        while day_count < max_spots_per_day and idx < n_candidates:
            spot = spots[idx]
            idx += 1
            sid = spot.get("id")
            if sid in scheduled_ids:
                continue

            # estimate travel from previous_spot (or origin on first day)
            travel_minutes = 0
            if previous_spot is not None:
                travel_info = get_travel_time(previous_spot, spot)
                travel_minutes = int(travel_info.get("travel_minutes") or 0)
            elif day_idx == 0 and filters.get("origin_latitude") and filters.get("origin_longitude"):
                origin = {
                    "latitude": filters["origin_latitude"],
                    "longitude": filters["origin_longitude"],
                }
                travel_info = get_travel_time(origin, spot)
                travel_minutes = int(travel_info.get("travel_minutes") or 0)
            else:
                travel_minutes = 15

            travel_end = _next_end_time(current_time, travel_minutes)
            # if travel already pushes beyond day's end, skip this spot
            if travel_end >= day_end:
                continue

            # lunch insertion check (time-of-day)
            if dt_time(11, 30) <= travel_end.time() <= dt_time(13, 30):
                lunch_start = travel_end
                lunch_end = _next_end_time(lunch_start, 60)
                if lunch_end > day_end:
                    # lunch would overflow the day, skip this spot
                    continue
                # insert lunch
                items.append({
                    "item_type": "meal",
                    "title": "午餐時間",
                    "start_time": lunch_start.strftime("%Y-%m-%d %H:%M"),
                    "end_time": lunch_end.strftime("%Y-%m-%d %H:%M"),
                    "stay_minutes": 60,
                    "travel_minutes": 0,
                    "meal_type": "午餐",
                    "notes": "依可用餐景點與時間窗安排。",
                })
                total_stay_minutes += 60
                current_time = lunch_end
            else:
                current_time = travel_end

            stay_minutes = int(spot.get("recommended_stay_minutes") or 60)
            stay_end = _next_end_time(current_time, stay_minutes)
            if stay_end > day_end:
                # this spot doesn't fit in this day's remaining time; skip it
                continue

            # accept this spot
            items.append({
                "item_type": "spot",
                "spot_id": sid,
                "title": spot.get("name"),
                "start_time": current_time.strftime("%Y-%m-%d %H:%M"),
                "end_time": stay_end.strftime("%Y-%m-%d %H:%M"),
                "stay_minutes": stay_minutes,
                "travel_minutes": travel_minutes,
                "meal_type": spot.get("meal_type"),
                "notes": f"{spot.get('region')}｜{spot.get('activity_type')}",
            })
            total_stay_minutes += stay_minutes
            total_travel_minutes += travel_minutes
            current_time = stay_end
            previous_spot = spot
            previous_spot_global = spot
            scheduled_ids.add(sid)
            day_count += 1

        # if we couldn't schedule any spot this day, record a reason
        if day_count == 0:
            rush_reasons.append(f"第 {day_idx+1} 日無可排入之景點。")

    # overall checks
    if (len(items) or 0) < 2:
        rush_reasons.append("行程站點數過少或條件過緊。")

    is_rushed = len(rush_reasons) > 0

    return {
        "status": "ok",
        "message": "已產生行程。",
        "items": items,
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
        "itinerary_length": itinerary_length,
        "total_travel_minutes": total_travel_minutes,
        "total_stay_minutes": total_stay_minutes,
        "is_rushed": is_rushed,
        "rush_reason": rush_reasons,
    }

