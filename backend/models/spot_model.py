from db import get_db


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
    rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_spot_by_id(spot_id):
    db = get_db()
    row = db.execute(
        """
        SELECT
            id,
            name,
            area,
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
        WHERE id = ?
        """,
        (spot_id,),
    ).fetchone()
    return dict(row) if row else None

