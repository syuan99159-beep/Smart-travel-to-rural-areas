import json


def _format_trip_context(trip_context: dict | None) -> str:
    trip_context = trip_context or {}
    lines = []

    origin = trip_context.get("origin")
    date = trip_context.get("date")
    start_time = trip_context.get("start_time")
    end_date = trip_context.get("end_date")
    end_time = trip_context.get("end_time")
    trip_length = trip_context.get("trip_length")
    area = trip_context.get("area")
    preferences = trip_context.get("preferences") or []

    if origin:
        lines.append(f"出發地點：{origin}")
    else:
        lines.append("未提供出發地，僅安排景點內行程，不計算出發車程。")
    if date:
        lines.append(f"出發日期：{date}")
    if start_time:
        lines.append(f"出發時間：{start_time}")
    if end_date:
        lines.append(f"結束日期：{end_date}")
    if end_time:
        lines.append(f"結束時間：{end_time}")
    if trip_length:
        lines.append(f"行程長度：{trip_length}")
    if area:
        lines.append(f"地區：{area}")
    if preferences:
        lines.append(f"偏好：{'、'.join(preferences)}")

    return "\n".join(lines)


def build_prompt(user_message: str, platform: str = "web", recent: int = 5, trip_context: dict | None = None) -> str:
    system_instructions = (
        "你是南投旅遊的助理。你應該用中文回覆，簡潔且友善，優先使用本系統資料庫的景點、活動與行程邏輯。"
    )

    prompt_parts = [system_instructions]
    context_text = _format_trip_context(trip_context)
    if context_text:
        prompt_parts.append("使用者提供的行程條件：\n" + context_text)
    prompt_parts.append("使用者查詢：\n" + user_message)
    prompt_parts.append("請簡短回覆，並在需要時引用景點 id 或建議加入行程的按鈕。")

    prompt = "\n\n".join(prompt_parts)
    print("[assistant] prompt preview =", prompt[:1000])
    return prompt


def build_itinerary_prompt(user_message: str, parsed_request: dict, itinerary_result: dict, trip_context: dict | None = None) -> str:
    system_instructions = (
        "你是南投智慧行程助理。你只能根據提供的資料庫查詢結果與路線驗證結果，整理成自然語言行程。"
        "不可以新增不存在的景點，不可以猜測車程、距離或路線，不可以編造資料。"
        "使用者指定 area 時，必須只使用該 area 的資料，不可改寫成其他地區。"
        "當使用者指定 area = 糯米橋 時，只能使用糯米橋資料。"
        "如果資料顯示目前使用系統估算車程，請明確寫出『目前使用系統估算車程』。"
        "請輸出 Markdown，並固定使用以下標題：### 行程名稱、### 建議行程、### 行程安排原因、### 路線合理性。"
    )

    compact = {
        "user_message": user_message,
        "parsed_request": parsed_request,
        "trip_context": trip_context or {},
        "itinerary": itinerary_result,
        "output_requirements": {
            "must_use_only_provided_spots": True,
            "must_not_invent_travel_time": True,
            "must_not_invent_destinations": True,
            "suggested_sections": ["行程名稱", "建議行程", "行程安排原因", "路線合理性"],
            "markdown_headings_required": True,
            "must_show_origin_date_start_time": True,
        },
    }

    prompt = "\n\n".join([
        system_instructions,
        "請先將以下行程條件原樣顯示在回覆前段：",
        _format_trip_context(trip_context),
        "請根據以下 JSON 內容改寫成完整行程說明：",
        json.dumps(compact, ensure_ascii=False, indent=2),
    ])
    print("[assistant] prompt preview =", prompt[:1000])
    return prompt


def format_itinerary_fallback(parsed_request: dict, itinerary_result: dict, trip_context: dict | None = None) -> str:
    summary = itinerary_result.get("summary") or {}
    items = itinerary_result.get("items") or []
    warnings = itinerary_result.get("warnings") or []
    trip_length = summary.get("trip_length") or parsed_request.get("trip_length") or "一日"
    area = parsed_request.get("area") or "南投"
    title = f"{area}{trip_length}智慧行程"
    context_text = _format_trip_context(trip_context)

    lines = [
        context_text,
        "### 行程名稱",
        title,
        "",
        "### 建議行程",
    ]

    for item in items:
        start_time = item.get("start_time", "")
        end_time = item.get("end_time", "")
        if item.get("type") == "spot":
            lines.append(f"- {start_time[-5:]} - {end_time[-5:]} {item.get('name', '未知景點')}")
            note = item.get("note") or ""
            if note:
                lines.append(f"  - {note}")
            travel_note = item.get("travel_note") or ""
            if travel_note:
                lines.append(f"  - {travel_note}")
            source = item.get("source")
            if source == "google_maps":
                lines.append(f"  - Google Maps 驗證車程：約 {item.get('travel_minutes', 0)} 分鐘")
            elif source == "same_place":
                lines.append("  - 兩個活動地點相近，可輕鬆步行前往")
            elif source == "fallback_maps":
                lines.append("  - 目前使用系統估算車程")
        elif item.get("type") == "meal":
            lines.append(f"- {start_time[-5:]} - {end_time[-5:]} 午餐／休息")

    lines.extend(["", "### 行程安排原因"])
    if parsed_request.get("preference"):
        lines.append(f"依據使用者偏好：{parsed_request.get('preference')}，優先安排相符的景點與路線。")
    else:
        lines.append("依據使用者需求與景點可用性，安排可執行的路線。")

    lines.extend(["", "### 路線合理性"])
    if any((item.get("source") == "fallback_maps") for item in items):
        lines.append("目前使用系統估算車程，若 Google Maps 可用時會優先使用真實路線驗證。")
    else:
        lines.append("已使用 Google Maps 或快取車程資訊檢查路線順序。")

    if warnings:
        lines.extend(["", "### 補充說明"])
        for warning in warnings:
            lines.append(f"- {warning}")

    lines.extend(["", "### 資料來源", "資料庫活動資料 + 路線驗證 + Gemini 整理回覆"])
    prompt = "\n".join(lines)
    print("[assistant] prompt preview =", prompt[:1000])
    return prompt
