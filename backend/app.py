from pathlib import Path

from flask import Flask, jsonify, render_template

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
from routes.maps import maps_bp
from routes.spots import spots_bp


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

    # apply CORS for API routes; allow origins via env CORS_ORIGINS (comma-separated) or default to '*'
    cors_origins = os.environ.get("CORS_ORIGINS", "*")
    if cors_origins == "*":
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
        CORS(app, resources={r"/api/*": {"origins": origins}})

    app.register_blueprint(spots_bp, url_prefix="/api")
    app.register_blueprint(itineraries_bp, url_prefix="/api")
    app.register_blueprint(maps_bp, url_prefix="/api")
    app.register_blueprint(line_bp, url_prefix="/api")

    app.teardown_appcontext(close_db)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    with app.app_context():
        init_db(app.config["DATABASE"])

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5003)
