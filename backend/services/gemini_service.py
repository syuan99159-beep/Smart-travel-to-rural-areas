import os
import requests
import json
from typing import Optional


def _get_config():
    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    return api_key, model


def generate_text(prompt: str, max_output_tokens: int = 512, temperature: float = 0.2, model: Optional[str] = None):
    """Call Google Generative API (Gemini) using an API key.

    Returns dict: {success: bool, text: str, raw: dict, error: str}
    """
    api_key, default_model = _get_config()
    model = model or default_model
    # Normalize model name: prefer plain model name like 'gemini-1.5-flash'.
    mapped = model
    # map deprecated/ambiguous names to a currently available model
    if mapped in ("gemini-pro", "gemini_pro"):
        mapped = "gemini-1.5-flash"
    # if user included 'models/' prefix, strip it because new endpoint expects the model id only
    if mapped.startswith("models/"):
        mapped = mapped.split("/", 1)[1]
    model = mapped

    if not api_key:
        return {"success": False, "text": "", "raw": None, "error": "GEMINI_API_KEY not set"}

    # Use the Generative Language `generateContent` endpoint (v1beta)
    # URL pattern: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        resp = requests.post(url, params={"key": api_key}, json=payload, timeout=20)
    except Exception as e:
        return {"success": False, "text": "", "raw": None, "error": str(e)}

    try:
        data = resp.json()
    except Exception:
        data = None

    if not resp.ok:
        err = None
        if isinstance(data, dict):
            err = data.get("error") or data.get("message")
        detail = data if data else resp.text
        hint = None
        if resp.status_code == 404:
            hint = "404 Not Found from Generative API — check that Generative Language API is enabled and the model name is correct."
        error_msg = err or f"HTTP {resp.status_code}: {hint or resp.reason}"
        return {"success": False, "text": "", "raw": detail, "error": error_msg}

    # Extract generated text from expected generateContent response shape:
    # data["candidates"][0]["content"]["parts"][0]["text"]
    text = ""
    try:
        if isinstance(data, dict) and data.get("candidates"):
            cand = data["candidates"][0]
            # candidate may contain 'content' which contains 'parts'
            content = cand.get("content") or cand.get("content")
            if content:
                # content could be a dict with 'parts' list
                parts = content.get("parts") if isinstance(content, dict) else None
                if parts and isinstance(parts, list) and len(parts) > 0:
                    first = parts[0]
                    text = first.get("text") or ""
        # fallback: try older shapes
        if not text and isinstance(data, dict):
            if data.get("output"):
                text = data.get("output")
            elif data.get("candidates") and isinstance(data.get("candidates")[0], dict):
                text = data.get("candidates")[0].get("output", "")
    except Exception:
        text = ""

    return {"success": True, "text": text, "raw": data, "error": None}
