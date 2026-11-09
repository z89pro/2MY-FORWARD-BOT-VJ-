"""
keep_alive.py
Smart Flask keep-alive for free-tier hosts (Render, Koyeb, Railway).
- Reads PORT from environment (Render injects this automatically)
- Flask starts in daemon thread → bot starts in main thread
- Both run simultaneously — web server never blocks the bot
"""
import os
import time
import threading
from flask import Flask, jsonify
from config import temp

app = Flask(__name__)
START_TIME = time.time()

@app.route("/")
def home():
    return "✅ Forward Bot is alive!", 200

@app.route("/health")
def health():
    uptime = time.time() - START_TIME
    active_forwards = len(getattr(temp, 'IS_FRWD_CHAT', []))
    lock_dict = getattr(temp, 'lock', {})
    active_locks = sum(1 for v in lock_dict.values() if v)
    
    status = "ok" if active_locks < 10 else "degraded"
    
    return jsonify({
        "status": status, 
        "uptime": uptime,
        "active_forwards": active_forwards,
        "active_locks": active_locks
    }), 200

def keep_alive():
    """
    Start Flask on the port Render/Koyeb provides via $PORT env var.
    Falls back to 8080 for local runs.
    Runs as daemon thread so it dies when the main process exits.
    """
    port = int(os.environ.get("PORT", 8080))

    thread = threading.Thread(
        target=lambda: app.run(
            host="0.0.0.0",
            port=port,
            use_reloader=False,   # MUST be False inside a thread
            debug=False,
        ),
        daemon=True,
        name="KeepAlive"
    )
    thread.start()
    print(f"[KeepAlive] ✅ Web server started on port {port}")
