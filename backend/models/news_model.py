from datetime import datetime, timezone

from db import get_db


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def replace_latest_news(items):
    db = get_db()
    fetched_at = _now_iso()

    db.execute("DELETE FROM latest_news")
    for index, item in enumerate(items):
        db.execute(
            """
            INSERT INTO latest_news (title, link, published_at, summary, source, sort_order, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("title", ""),
                item.get("link", ""),
                item.get("published_at", ""),
                item.get("summary", ""),
                item.get("source", ""),
                int(item.get("sort_order", index)),
                fetched_at,
            ),
        )

    db.commit()


def get_latest_news(limit=5):
    db = get_db()
    rows = db.execute(
        """
        SELECT title, link, published_at, summary, source, sort_order, fetched_at
        FROM latest_news
        ORDER BY sort_order ASC, published_at DESC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    return [dict(row) for row in rows]


def get_latest_news_last_fetched_at():
    db = get_db()
    row = db.execute("SELECT MAX(fetched_at) AS fetched_at FROM latest_news").fetchone()
    if not row or not row["fetched_at"]:
        return None

    try:
        return datetime.fromisoformat(row["fetched_at"])
    except ValueError:
        return None


def has_latest_news():
    db = get_db()
    row = db.execute("SELECT 1 FROM latest_news LIMIT 1").fetchone()
    return bool(row)