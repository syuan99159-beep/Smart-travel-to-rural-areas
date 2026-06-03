from pathlib import Path

from flask import Flask, jsonify, render_template, request

from config import Config
from dotenv import load_dotenv
import os
from flask_cors import CORS

# load .env if present
load_dotenv()
os.environ.setdefault("USE_REAL_MAPS", os.environ.get("USE_REAL_MAPS", "false"))
from db import close_db, init_db
from routes.itineraries import itineraries_bp
from routes.line import line_bp
from routes.news import news_bp
from routes.maps import maps_bp
from routes.spots import spots_bp
from routes.filters import filters_bp
from routes.assistant import assistant_bp
from services.line_service import process_line_webhook_request
from services.news_service import refresh_latest_news, start_latest_news_refresh_loop


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"


def create_app():
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR),
        static_folder=str(FRONTEND_DIR),
        static_url_path="",
    )
    app.config.from_object(Config)

    # Small health-check: do not print the key, only whether it's loaded
    try:
        key_loaded = bool(os.environ.get("GEMINI_API_KEY"))
        app.logger.info(f"GEMINI_API_KEY loaded: {key_loaded}")
    except Exception:
        app.logger.info("GEMINI_API_KEY loaded: unknown")

    # apply CORS for API routes; allow origins via env CORS_ORIGINS (comma-separated) or default to '*'
    cors_origins = os.environ.get("CORS_ORIGINS", "*")
    if cors_origins == "*":
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
        CORS(app, resources={r"/api/*": {"origins": origins}})

    app.register_blueprint(spots_bp, url_prefix="/api")
    app.register_blueprint(filters_bp, url_prefix="/api")
    app.register_blueprint(itineraries_bp, url_prefix="/api")
    app.register_blueprint(news_bp, url_prefix="/api")
    app.register_blueprint(maps_bp, url_prefix="/api")
    app.register_blueprint(assistant_bp, url_prefix="/api")
    app.register_blueprint(line_bp, url_prefix="/api")
    print(app.url_map)

    app.teardown_appcontext(close_db)

    @app.route("/")
    def home():
        print("[home] serving index =", (FRONTEND_DIR / "index.html").resolve())
        return render_template("index.html")

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/callback")
    def line_callback():
        result = process_line_webhook_request(
            request.get_data(),
            request.headers,
            reply_to_line=True,
            require_signature=True,
        )
        return jsonify({k: v for k, v in result.items() if k != "status_code"}), result.get("status_code", 200)

    with app.app_context():
        # initialize DB only if it does not exist or when explicitly forced
        db_path = Path(app.config["DATABASE"])
        force_init = os.environ.get("FORCE_INIT_DB", "").lower() in ("1", "true", "yes")
        if not db_path.exists() or force_init:
            init_db(app.config["DATABASE"])
        else:
            app.logger.info("database exists, skipping init_db()")
        try:
            refresh_latest_news(force=True)
        except Exception:
            app.logger.exception("初始化南投旅遊網最新消息失敗")

    start_latest_news_refresh_loop(app)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
    host="127.0.0.1",
    port=5004,
    debug=True,
    use_reloader=False
)
