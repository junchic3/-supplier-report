#!/usr/bin/env python3
"""
Flask web app for Chinese Manufacturer Finder
Run: python app.py
Visit: http://localhost:5000
"""

import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, request

BASE_DIR    = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

PRODUCTS_META = {
    "claw_hammer": {
        "name_cn": "羊角榔头（带吸铁石）",
        "name_en": "Claw Hammer with Magnet",
        "icon": "🔨",
        "note": "锤头带磁铁/吸铁石功能，V型羊角，合金钢锤头优先",
        "weights": {
            "magnet_feature": 30, "material_quality": 20, "handle_quality": 13,
            "is_manufacturer": 12, "certification": 13, "location_score": 12,
        },
    },
    "caulking_gun": {
        "name_cn": "硅胶枪（打胶器）",
        "name_en": "Caulking Gun / Silicone Sealant Gun",
        "icon": "🔫",
        "note": "适配300ml标准管，止流防滴漏功能，全钢枪架优先",
        "weights": {
            "anti_drip": 25, "frame_material": 20, "compatibility": 18,
            "is_manufacturer": 12, "certification": 13, "location_score": 12,
        },
    },
    "triangle_scraper": {
        "name_cn": "三角刮刀",
        "name_en": "Triangle / Triangular Scraper",
        "icon": "🔧",
        "note": "SK5高碳钢刀片，适合刮除硅胶/腻子，防滑手柄设计",
        "weights": {
            "blade_material": 32, "handle_design": 20, "multi_function": 16,
            "is_manufacturer": 12, "certification": 10, "location_score": 10,
        },
    },
}

def load_latest() -> dict:
    files = sorted(RESULTS_DIR.glob("*.json"), reverse=True)
    if not files:
        return {}
    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)
    return data, files[0].stem   # (data, date_str)

@app.route("/")
def index():
    try:
        data, date_str = load_latest()
    except (TypeError, ValueError):
        data, date_str = {}, "—"
    return render_template("index.html",
                           data=data,
                           date_str=date_str,
                           meta=PRODUCTS_META)

@app.route("/api/data")
def api_data():
    try:
        data, date_str = load_latest()
        return jsonify({"ok": True, "date": date_str, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/run", methods=["POST"])
def api_run():
    """Trigger a fresh scrape in the background."""
    try:
        script = BASE_DIR / "manufacturer_finder.py"
        subprocess.Popen(
            [sys.executable, str(script)],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return jsonify({"ok": True, "message": "Scrape started. Refresh in ~3 minutes."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Manufacturer Finder Web App on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
