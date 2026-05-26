from services.itinerary_service import generate_itinerary


REGIONS = ["小半天", "大雁", "糯米橋"]
ACTIVITY_TYPES = ["DIY", "親子", "食農教育", "生態導覽", "戶外", "咖啡"]
DURATION_MAP = {"半日": "half_day", "一日": "full_day"}
STAY_LEVEL_MAP = {"短": "short", "中": "medium", "長": "long"}


def parse_fixed_format(text):
    normalized = " ".join((text or "").split())
    tokens = normalized.split(" ") if normalized else []

    filters = {
        "raw_text": normalized,
        "region": None,
        "activity_type": None,
        "itinerary_length": None,
        "stay_level": None,
        "budget_level": None,
        "indoor_outdoor": None,
        "keyword": None,
    }

    keywords = []
    for token in tokens:
        if token in REGIONS:
            filters["region"] = token
            continue
        if token in ACTIVITY_TYPES:
            filters["activity_type"] = token
            continue
        if token in DURATION_MAP:
            filters["itinerary_length"] = DURATION_MAP[token]
            continue
        if token in STAY_LEVEL_MAP:
            filters["stay_level"] = token
            continue
        if token in ("不要戶外", "不要室內"):
            filters["indoor_outdoor"] = "室內"
            continue
        if token == "戶外":
            filters["indoor_outdoor"] = "戶外"
            continue
        if token == "室內":
            filters["indoor_outdoor"] = "室內"
            continue
        if token in ("低預算", "中預算", "高預算"):
            filters["budget_level"] = token.replace("預算", "")
            continue
        keywords.append(token)

    if keywords:
        filters["keyword"] = " ".join(keywords)

    missing = []
    if not filters["itinerary_length"]:
        missing.append("行程長度（半日 / 一日）")

    return {
        "filters": filters,
        "missing": missing,
        "is_complete": len(missing) == 0,
    }


def build_line_reply(text):
    parsed = parse_fixed_format(text)
    if not parsed["is_complete"]:
        return {
            "message": "請補上行程長度，例如：半日 或 一日。",
            "parsed": parsed,
        }

    itinerary = generate_itinerary(
        {
            **parsed["filters"],
            "start_time": "09:00",
            "end_time": "17:00" if parsed["filters"]["itinerary_length"] == "full_day" else "13:00",
            "origin": "LINE 使用者起點",
        }
    )

    return {
        "message": itinerary.get("message", "已完成推薦。"),
        "parsed": parsed,
        "itinerary": itinerary,
    }

