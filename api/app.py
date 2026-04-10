"""
Flask application factory for DarkShield API.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import joblib
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.public_routes import pub, v1_categories, v1_leaderboard, v1_score, v1_stats
from api.routes import bp
from ml.database.transparency_db import init_db
from ml.models.confirm_shaming_nlp import ConfirmShamingNLP


def create_app() -> Flask:
    """Create and configure the Flask app; load ML models once."""
    load_dotenv(_ROOT / ".env")
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db_path = os.getenv("DARKSHIELD_DB_PATH", str(_ROOT / "data" / "darkshield.db"))
    model_path = os.getenv("DARKSHIELD_MODEL_PATH", str(_ROOT / "ml" / "models" / "saved" / "darkshield_rf.pkl"))
    cs_path = os.getenv(
        "DARKSHIELD_CONFIRM_PATH",
        str(_ROOT / "ml" / "models" / "saved" / "confirm_shaming_tfidf.pkl"),
    )

    init_db(db_path)
    app.config["DB_PATH"] = db_path
    app.config["ROOT"] = str(_ROOT)
    app.config["MODEL_PIPELINE"] = joblib.load(model_path)
    app.config["CONFIRM_SHAMING"] = ConfirmShamingNLP.load(Path(cs_path))

    app.register_blueprint(bp)
    app.register_blueprint(pub)
    limiter = Limiter(get_remote_address, app=app, storage_uri="memory://", default_limits=[])
    for view in (v1_score, v1_leaderboard, v1_categories, v1_stats):
        limiter.limit("100 per hour")(view)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
