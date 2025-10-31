# app.py
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading, time, json, os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

SHARED_FILE = "/home/phil/Desktop/wro/webapp/shared_data.json"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    """Fallback REST endpoint if SocketIO isn't supported."""
    if os.path.exists(SHARED_FILE):
        with open(SHARED_FILE) as f:
            return jsonify(json.load(f))
    return jsonify({})

# Background thread to broadcast new data every second
def data_emitter():
    last_data = None
    while True:
        try:
            if os.path.exists(SHARED_FILE):
                with open(SHARED_FILE) as f:
                    data = json.load(f)
                if data != last_data:
                    socketio.emit("update", data)
                    last_data = data
        except Exception as e:
            print("Emitter error:", e)
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=data_emitter, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000)
