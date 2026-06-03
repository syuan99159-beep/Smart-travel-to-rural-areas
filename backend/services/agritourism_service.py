import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from models.spot_model import create_spot_if_missing


SOURCE_URL = "https://travel.nantou.gov.tw/nantou-agritourism/"
IMAGE_SAVE_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "assets" / "images" / "activities"
IMAGE_SAVE_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_filename(url):
    path = urlparse(url).path
    name = os.path.basename(path)
    return re.sub(r"[^0-9A-Za-z\-\._\u4e00-\u9fff]+", "_", name)


def _download_image(url):
    if not url:
        return ''

    filename = _sanitize_filename(url)
    dest = IMAGE_SAVE_DIR / filename
    if dest.exists():
        return str(Path('assets/images/activities') / filename)

    try:
        resp = requests.get(url, stream=True, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        with open(dest, 'wb') as fh:
            for chunk in resp.iter_content(1024 * 8):
                fh.write(chunk)
        return str(Path('assets/images/activities') / filename)
    except Exception:
        return ''


def _extract_items_from_html(html_text):
    items = []

    # Patterns: original '│...' paragraphs and Elementor heading blocks
    title_pattern = re.compile(r"<p[^>]*?>\s*│([^<]+)</p>", re.IGNORECASE)
    elementor_title_pattern = re.compile(r"<div[^>]*class=[\"'][^\"']*elementor-heading-title[^\"']*[\"'][^>]*>\s*(<p[^>]*>.*?</p>|([^<]+))\s*</div>", re.IGNORECASE | re.DOTALL)
    img_pattern = re.compile(r"<img[^>]+?src=[\"']([^\"']+)[\"']", re.IGNORECASE)
    span_pattern = re.compile(r"<span[^>]*?>(.*?)</span>", re.IGNORECASE | re.DOTALL)

    # collect title matches with positions so we can search forward for images/description
    title_positions = []
    for m in title_pattern.finditer(html_text):
        title_positions.append((m.start(), m.end(), re.sub(r'<[^>]+>', '', m.group(1) or '').strip()))

    for m in elementor_title_pattern.finditer(html_text):
        inner = m.group(1) or m.group(2) or ''
        text = re.sub(r'<[^>]+>', '', inner or '').strip()
        if text:
            title_positions.append((m.start(), m.end(), text))

    # sort by position
    title_positions.sort(key=lambda x: x[0])

    for start_pos, end_pos, title in title_positions:
        # look for first image after the title end
        img_match = img_pattern.search(html_text, pos=end_pos)
        image_url = img_match.group(1).strip() if img_match else ''
        if image_url and image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif image_url and image_url.startswith('/'):
            image_url = urljoin(SOURCE_URL, image_url)

        # find first meaningful span/text after image or title
        span_match = None
        search_start = img_match.end() if img_match else end_pos
        for s in span_pattern.finditer(html_text, pos=search_start):
            text = re.sub(r'<[^>]+>', '', s.group(1) or '').strip()
            if text and len(text) > 20:
                span_match = text
                break

        description = span_match or ''

        items.append({
            'title': title,
            'image_url': image_url,
            'description': re.sub(r'\s+', ' ', description).strip(),
        })

    return items


def import_agritourism(source_url=SOURCE_URL, limit=10):
    resp = requests.get(source_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    html_text = resp.text

    items = _extract_items_from_html(html_text)
    imported = []

    def _classify(title, description):
        txt = (title or '') + ' ' + (description or '')
        txt = txt.lower()
        if any(k in txt for k in ['diy', '手作', '體驗', 'workshop']):
            return 'DIY'
        if any(k in txt for k in ['美食', '餐', '小吃', '在地']):
            return '在地美食'
        if any(k in txt for k in ['文化', '導覽', '文史', '導览']):
            return '文化導覽'
        if any(k in txt for k in ['生態', '生態', '自然', '步道', '觀察']):
            return '生態之旅'
        return '生態之旅'

    def _extract_keywords(title, description):
        text = ((title or '') + ' ' + (description or '')).strip()
        # simple keyword extraction: split by non-word and take frequent words >2 chars
        words = re.findall(r'[\w\u4e00-\u9fff]{2,}', text)
        freq = {}
        for w in words:
            lw = w.lower()
            freq[lw] = freq.get(lw, 0) + 1
        # sort by frequency and take top 4
        keys = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return ','.join([k for k, v in keys[:4]])

    for item in items[:limit]:
        image_path = _download_image(item.get('image_url'))
        category = _classify(item.get('title'), item.get('description'))
        keywords = _extract_keywords(item.get('title'), item.get('description')) or '農遊,生態'

        payload = {
            'name': item.get('title'),
            'area': '埔里',
            'category': category,
            'trip_length': '一日',
            'stay_type': '中',
            'stay_minutes': 90,
            'budget': '中',
            'indoor_outdoor': '戶外',
            'can_dine': 0,
            'meal_type': '無',
            'description': item.get('description'),
            'image': image_path,
            'keywords': keywords,
        }

        try:
            spot_id = create_spot_if_missing(payload)
            imported.append({'id': spot_id, 'name': payload['name'], 'image': payload['image']})
        except Exception:
            continue

    return imported
