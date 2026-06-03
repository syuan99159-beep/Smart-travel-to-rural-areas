from difflib import SequenceMatcher
from pathlib import Path

from db import get_db


ACTIVITY_IMAGE_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "assets" / "images" / "activities"


def _normalize_text(value):
    return ''.join(ch for ch in str(value or '').strip().lower() if ch.isalnum() or '\u4e00' <= ch <= '\u9fff')


def _resolve_image_path(name, image_path):
    if not image_path:
        return ''

    candidate_path = Path(image_path)
    existing_path = Path(__file__).resolve().parent.parent.parent / 'frontend' / candidate_path
    if existing_path.exists():
        return str(candidate_path).replace('\\', '/')

    if not ACTIVITY_IMAGE_DIR.exists():
        return image_path

    normalized_name = _normalize_text(name)
    files = [path for path in ACTIVITY_IMAGE_DIR.iterdir() if path.is_file()]
    if not files:
        return image_path

    exact_matches = []
    fuzzy_matches = []
    for path in files:
        stem = _normalize_text(path.stem)
        if normalized_name and stem == normalized_name:
            exact_matches.append(path)
            continue

        if normalized_name and (normalized_name in stem or stem in normalized_name):
            fuzzy_matches.append((1.0, path))
            continue

        score = SequenceMatcher(None, normalized_name, stem).ratio()
        fuzzy_matches.append((score, path))

    if exact_matches:
        return str(Path('assets/images/activities') / exact_matches[0].name)

    if fuzzy_matches:
        fuzzy_matches.sort(key=lambda item: item[0], reverse=True)
        return str(Path('assets/images/activities') / fuzzy_matches[0][1].name)

    return image_path


def _resolve_spot_image(row):
    image = row.get('image') or ''
    resolved_image = _resolve_image_path(row.get('name'), image)
    if resolved_image != image:
        row['image'] = resolved_image
    return row


def _first_non_empty(filters, keys):
    for key in keys:
        value = filters.get(key)
        if value not in (None, "", "all"):
            return value
    return None


def _normalize_boolean(value):
    if value in (True, 1, "1", "true", "True"):
        return 1
    if value in (False, 0, "0", "false", "False"):
        return 0
    return None


def build_spot_filters(filters):
    clauses = ["is_active = 1"]
    params = []

    area = _first_non_empty(filters, ["area", "region"])
    category = _first_non_empty(filters, ["category", "activity_type"])
    trip_length = _first_non_empty(filters, ["trip_length", "duration"])
    stay_type = _first_non_empty(filters, ["stay_type", "stay_level"])
    indoor_outdoor = _first_non_empty(filters, ["indoor_outdoor", "space"])
    budget = _first_non_empty(filters, ["budget", "budget_level"])
    keyword = _first_non_empty(filters, ["keyword", "search"])
    can_dine = _normalize_boolean(filters.get("can_dine"))

    if area:
        clauses.append("area = ?")
        params.append(area)

    if category:
        clauses.append("category = ?")
        params.append(category)

    if trip_length:
        clauses.append("trip_length = ?")
        params.append(trip_length)

    if stay_type:
        clauses.append("stay_type = ?")
        params.append(stay_type)

    if indoor_outdoor:
        clauses.append("indoor_outdoor = ?")
        params.append(indoor_outdoor)

    if budget:
        clauses.append("budget = ?")
        params.append(budget)

    if can_dine in (0, 1):
        clauses.append("can_dine = ?")
        params.append(can_dine)

    if keyword:
        clauses.append("(name LIKE ? OR category LIKE ? OR description LIKE ? OR keywords LIKE ?)")
        keyword_value = f"%{keyword}%"
        params.extend([keyword_value, keyword_value, keyword_value, keyword_value])

    where_sql = " AND ".join(clauses)
    limit_sql = ""
    if filters.get("limit"):
        limit_sql = " LIMIT ?"
        params.append(int(filters["limit"]))

    return where_sql, params, limit_sql


def list_spots(filters=None):
    filters = filters or {}
    where_sql, params, limit_sql = build_spot_filters(filters)
    query = f"""
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
        WHERE {where_sql}
        ORDER BY area, name
        {limit_sql}
    """
    db = get_db()
    rows = db.execute(query, params).fetchall()
    return [_resolve_spot_image(dict(row)) for row in rows]


def get_spot_by_id(spot_id):
    db = get_db()
    row = db.execute(
        """
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
        WHERE id = ?
        """,
        (spot_id,),
    ).fetchone()
    return _resolve_spot_image(dict(row)) if row else None


def get_spot_by_name(name):
    db = get_db()
    row = db.execute(
        "SELECT id, name FROM spots WHERE name = ?",
        (name,),
    ).fetchone()
    return dict(row) if row else None


def create_spot(payload):
    db = get_db()
    now = __import__('datetime').datetime.now().isoformat(timespec='seconds')

    db.execute(
        """
        INSERT INTO spots (name, area, category, trip_length, stay_type, stay_minutes, budget, indoor_outdoor, can_dine, meal_type, description, image, keywords, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get('name'),
            payload.get('area') or payload.get('region') or '其他',
            payload.get('category') or payload.get('type') or '生態之旅',
            payload.get('trip_length') or payload.get('duration') or '一日',
            payload.get('stay_type') or payload.get('stay') or '中',
            int(payload.get('stay_minutes') or payload.get('recommended_stay_minutes') or 90),
            payload.get('budget') or '中',
            payload.get('indoor_outdoor') or payload.get('space') or '戶外',
            1 if payload.get('can_dine') in (1, True, '1', 'true', 'True') else 0,
            payload.get('meal_type') or '無',
            payload.get('description') or '',
            payload.get('image') or '',
            payload.get('keywords') or '',
            1,
            now,
        ),
    )
    db.commit()
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def create_spot_if_missing(payload):
    existing = get_spot_by_name(payload.get('name'))
    if existing:
        return existing['id']
    return create_spot(payload)

