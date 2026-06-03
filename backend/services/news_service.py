import html
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

from models.news_model import (
    get_latest_news,
    get_latest_news_last_fetched_at,
    has_latest_news,
    replace_latest_news,
)


NEWS_FEED_URL = "https://travel.nantou.gov.tw/category/news-press/feed/"
NEWS_REFRESH_INTERVAL_SECONDS = 60 * 60 * 12
_REFRESH_LOCK = threading.RLock()
_REFRESH_THREAD_STARTED = False


def _clean_text(value):
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_pub_date(value):
    if not value:
        return datetime.now(timezone.utc)

    try:
        return datetime.strptime(value.strip(), "%a, %d %b %Y %H:%M:%S %z")
    except ValueError:
        return datetime.now(timezone.utc)


def _parse_rss_feed(xml_text, limit=5):
    root = ET.fromstring(xml_text)
    items = []

    for index, item in enumerate(root.findall("./channel/item")):
        title = _clean_text(item.findtext("title"))
        link = _clean_text(item.findtext("link"))
        published_at = _parse_pub_date(item.findtext("pubDate")).astimezone(timezone.utc).isoformat(timespec="seconds")
        summary = _clean_text(item.findtext("description"))

        if not title or not link:
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "published_at": published_at,
                "summary": summary,
                "source": NEWS_FEED_URL,
                "sort_order": index,
            }
        )

        if len(items) >= limit:
            break

    return items


def _is_cache_stale(now=None):
    last_fetched_at = get_latest_news_last_fetched_at()
    if not last_fetched_at:
        return True

    now = now or datetime.now(timezone.utc)
    if last_fetched_at.tzinfo is None:
        last_fetched_at = last_fetched_at.replace(tzinfo=timezone.utc)

    return now - last_fetched_at >= timedelta(seconds=NEWS_REFRESH_INTERVAL_SECONDS)


def refresh_latest_news(force=False, limit=5):
    with _REFRESH_LOCK:
        if not force and has_latest_news() and not _is_cache_stale():
            return get_latest_news(limit)

        response = requests.get(
            NEWS_FEED_URL,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NantouNewsBot/1.0)"},
        )
        response.raise_for_status()

        items = _parse_rss_feed(response.text, limit=limit)
        if not items:
            raise RuntimeError("南投旅遊網 RSS 沒有可用最新消息")

        replace_latest_news(items)
        return get_latest_news(limit)


def get_latest_news_payload(limit=5):
    with _REFRESH_LOCK:
        if not has_latest_news() or _is_cache_stale():
            try:
                return refresh_latest_news(force=True, limit=limit)
            except Exception:
                if has_latest_news():
                    return get_latest_news(limit)
                raise

        return get_latest_news(limit)


def start_latest_news_refresh_loop(app):
    global _REFRESH_THREAD_STARTED

    if _REFRESH_THREAD_STARTED:
        return

    _REFRESH_THREAD_STARTED = True

    def _run():
        while True:
            try:
                with app.app_context():
                    refresh_latest_news(force=True)
            except Exception:
                app.logger.exception("南投旅遊網最新消息更新失敗")

            time.sleep(NEWS_REFRESH_INTERVAL_SECONDS)

    thread = threading.Thread(target=_run, name="latest-news-refresh", daemon=True)
    thread.start()