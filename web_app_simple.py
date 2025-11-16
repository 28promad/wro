# web_app_simple.py
# Simplified Flask dashboard (polling-based, no WebSockets)
# Use this if you have issues with flask-socketio
# Run: python web_app_simple.py

from flask import Flask, render_template, jsonify, request
import json
from rover_data_service import get_service
from datetime import datetime

app = Flask(__name__)
service = get_service()


@app.route('/')
def index():
    """Serve the main dashboard page."""
    return render_template('dashboard_simple.html')


@app.route('/api/current')
def get_current_data():
    """REST endpoint for current sensor data."""
    return jsonify(service.get_current())


@app.route('/api/history')
def get_history_data():
    """REST endpoint for historical sensor data."""
    limit = request.args.get('limit', 100, type=int)
    return jsonify({
        'history': service.get_history(limit)
    })


@app.route('/api/graphs')
def get_graph_data():
    """REST endpoint for graph data (time-series)."""
    limit = request.args.get('limit', 100, type=int)
    return jsonify(service.get_graph_data(limit))


@app.route('/api/status')
def get_status():
    """REST endpoint for connection status."""
    current = service.get_current()
    return jsonify({
        'connected': current['connected'],
        'timestamp': current['timestamp'],
        'data_points': len(service.get_history())
    })


if __name__ == '__main__':
    print("Starting Databot Rover Dashboard (Polling Mode)...")
    print("Access at: http://<pi-ip>:5000")
    print("\nNote: This version uses polling (2-second updates).")
    print("For real-time updates, use web_app.py with flask-socketio.")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
