from __future__ import annotations
import os
from flask import Flask, send_from_directory, redirect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Redirect "/" → "/arcade"
@app.get("/")
def root():
    return redirect("/arcade", code=302)

# Serve the game page
@app.get("/arcade")
def arcade():
    # static/game/index.html exists
    return send_from_directory("static/game", "index.html")

# Serve the web app manifest (root scope)
@app.get("/manifest.json")
def manifest():
    return send_from_directory(
        BASE_DIR, "manifest.json", mimetype="application/manifest+json"
    )

# Serve the service worker (root scope) + no-cache headers
@app.get("/service-worker.js")
def service_worker():
    resp = send_from_directory(
        BASE_DIR, "service-worker.js", mimetype="application/javascript"
    )
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

# Optional healthcheck for Render
@app.get("/health")
def health():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
