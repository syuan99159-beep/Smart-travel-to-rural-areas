from db import get_db
from datetime import datetime


def build_cache_row(origin_key, destination_key, travel_minutes, distance_text, duration_text, source):
    return {
        "origin_key": origin_key,
        "destination_key": destination_key,
        "travel_minutes": int(travel_minutes or 0),
        "distance_text": distance_text,
        "duration_text": duration_text,
        "source": source,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def get_travel_cache(origin_key, destination_key):
    db = get_db()
    row = db.execute(
        "SELECT * FROM travel_cache WHERE origin_key = ? AND destination_key = ?",
        (origin_key, destination_key),
    ).fetchone()
    return dict(row) if row else None


def save_travel_cache(origin_key, destination_key, travel_minutes, distance_text, duration_text, source):
    db = get_db()
    now = datetime.now().isoformat(timespec="seconds")
    # Try update first
    existing = db.execute(
        "SELECT id FROM travel_cache WHERE origin_key = ? AND destination_key = ?",
        (origin_key, destination_key),
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE travel_cache SET travel_minutes = ?, distance_text = ?, duration_text = ?, source = ?, updated_at = ? WHERE id = ?",
            (int(travel_minutes or 0), distance_text, duration_text, source, now, existing[0]),
        )
    else:
        db.execute(
            "INSERT INTO travel_cache (origin_key, destination_key, travel_minutes, distance_text, duration_text, source, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (origin_key, destination_key, int(travel_minutes or 0), distance_text, duration_text, source, now),
        )
    db.commit()
