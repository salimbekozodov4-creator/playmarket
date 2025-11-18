"""
Small Flask server to serve mini-app store.

All app files and images are stored on Telegram servers.
This server fetches them via the Telegram Bot API when requested.

Usage (for local testing):
1. Install requirements: `pip install -r requirements.txt`
2. Run this server: `python server.py`
3. Expose it with ngrok for Telegram WebApp (must be HTTPS):
   `ngrok http 5000` and set `WEBAPP_BASE_URL` to the https ngrok URL.
"""
from flask import Flask, send_from_directory, abort, jsonify, redirect
import os
import json
import logging
import asyncio
from telegram import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
WEB_DIR = os.path.join(BASE_DIR, "web")
APPS_FILE = os.path.join(BASE_DIR, "apps.json")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/apps.json", methods=["GET"])
def apps_json():
    # Serve the apps list with Telegram file IDs and photo URLs
    try:
        with open(APPS_FILE, "r", encoding="utf-8") as f:
            data = f.read()
        return app.response_class(data, mimetype="application/json")
    except Exception:
        return jsonify([])


@app.route("/photo/<file_id>")
def get_photo(file_id):
    """Redirect to Telegram photo URL or fetch and cache."""
    if not bot:
        return jsonify({"error": "Bot token not configured"}), 500
    
    try:
        # Get file from Telegram
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        file_info = loop.run_until_complete(bot.get_file(file_id))
        loop.close()
        
        # Construct the download URL
        photo_url = file_info.file_path
        if photo_url.startswith('/'):
            photo_url = 'https://api.telegram.org/file/bot' + BOT_TOKEN + photo_url
        
        return redirect(photo_url, code=302)
    except Exception as e:
        logger.error("Failed to get photo: %s", e)
        return jsonify({"error": "Failed to fetch photo"}), 404


@app.route("/download/<file_id>")
def download_file(file_id):
    """Download app file from Telegram."""
    if not bot:
        return jsonify({"error": "Bot token not configured"}), 500
    
    try:
        # Get file from Telegram
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        file_info = loop.run_until_complete(bot.get_file(file_id))
        loop.close()
        
        # Construct the download URL
        file_url = file_info.file_path
        if file_url.startswith('/'):
            file_url = 'https://api.telegram.org/file/bot' + BOT_TOKEN + file_url
        
        return redirect(file_url, code=302)
    except Exception as e:
        logger.error("Failed to download file: %s", e)
        return jsonify({"error": "Failed to download file"}), 404


@app.route("/<path:filename>")
def serve_file(filename):
    base = app.static_folder
    path = os.path.join(base, filename)
    # Prevent path traversal
    try:
        if os.path.exists(path) and os.path.commonpath([os.path.abspath(path), os.path.abspath(base)]) == os.path.abspath(base):
            return send_from_directory(base, filename)
    except Exception:
        pass
    abort(404)


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("WARNING: TELEGRAM_BOT_TOKEN not set. Photo and file downloads will not work.")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
