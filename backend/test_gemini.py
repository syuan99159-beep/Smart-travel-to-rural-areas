import os
import sys
import json

# allow running from repository root
sys.path.insert(0, os.path.dirname(__file__))

from services.gemini_service import generate_text


def main():
    print("GEMINI_API_KEY loaded:", bool(os.environ.get("GEMINI_API_KEY")))
    print("Using model from env GEMINI_MODEL:", os.environ.get("GEMINI_MODEL"))
    res = generate_text("測試連線（來自 test_gemini.py）", max_output_tokens=128)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
