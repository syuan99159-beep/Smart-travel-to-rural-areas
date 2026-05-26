import json
from datetime import datetime

from db import get_db


def create_itinerary(payload, items):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO itineraries (
            query_json,
            start_time,
            end_time,
            itinerary_length,
            origin_label,
            total_stay_minutes,
            total_travel_minutes,
            is_rushed,
            rush_reason,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            json.dumps(payload, ensure_ascii=False),
            payload.get("start_time"),
            payload.get("end_time"),
            payload.get("trip_length") or payload.get("itinerary_length"),
            payload.get("start_point") or payload.get("origin", "起點"),
            payload.get("total_stay_minutes", 0),
            payload.get("total_travel_minutes", 0),
            1 if payload.get("is_rushed") else 0,
            json.dumps(payload.get("rush_reason", []), ensure_ascii=False),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    itinerary_id = cursor.lastrowid

    for index, item in enumerate(items, start=1):
        item_type = item.get("item_type") or item.get("type") or "spot"
        title = item.get("title") or item.get("name") or ""
        notes = item.get("notes") or item.get("note") or ""
        db.execute(
            """
            INSERT INTO itinerary_items (
                itinerary_id,
                item_order,
                item_type,
                spot_id,
                title,
                start_time,
                end_time,
                stay_minutes,
                travel_minutes,
                meal_type,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                itinerary_id,
                index,
                item_type,
                item.get("spot_id"),
                title,
                item.get("start_time"),
                item.get("end_time"),
                item.get("stay_minutes", 0),
                item.get("travel_minutes", 0),
                item.get("meal_type", "無"),
                notes,
            ),
        )

    db.commit()
    return itinerary_id


def get_itinerary(itinerary_id):
    db = get_db()
    itinerary_row = db.execute(
        "SELECT * FROM itineraries WHERE id = ?",
        (itinerary_id,),
    ).fetchone()

    if not itinerary_row:
        return None

    item_rows = db.execute(
        "SELECT * FROM itinerary_items WHERE itinerary_id = ? ORDER BY item_order",
        (itinerary_id,),
    ).fetchall()

    return {
        "itinerary": dict(itinerary_row),
        "items": [dict(row) for row in item_rows],
    }

