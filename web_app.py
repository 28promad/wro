# web_app.py
# Flask web application for real-time Databot rover dashboard
# Run this on the Raspberry Pi: python web_app.py
# Then access at: http://<pi-ip>:5000

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import json
from rover_data_service import get_service
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rover_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

service = get_service()
connected_clients = set()


# ==================== Flask Routes ====================

@app.route('/')
def index():
    """Serve the main dashboard page."""
    return render_template('dashboard.html')


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


# ==================== WebSocket Events ====================

@socketio.on('connect')
def handle_connect():
    """Handle new client connection."""
    from flask_socketio import request
    print(f"Client connected: {request.sid}")
    connected_clients.add(request.sid)
    
    # Send current data immediately
    current = service.get_current()
    emit('update', current)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    from flask_socketio import request
    print(f"Client disconnected: {request.sid}")
    connected_clients.discard(request.sid)


@socketio.on('request_graph_data')
def handle_graph_request(data):
    """Handle request for graph data."""
    limit = data.get('limit', 100)
    graph_data = service.get_graph_data(limit)
    emit('graph_data', graph_data)


@socketio.on('request_status')
def handle_status_request():
    """Handle request for current status."""
    current = service.get_current()
    emit('status_update', {
        'connected': current['connected'],
        'timestamp': current['timestamp'],
        'data_points': len(service.get_history())
    })


# ==================== Data Service Listener ====================

def on_data_update(data):
    """Callback called when rover data is updated."""
    # Broadcast to all connected clients using socketio
    socketio.emit('update', data, to=None, skip_sid=None)


# Register the listener with the data service
service.add_listener(on_data_update)


# ==================== Entry Point ====================

if __name__ == '__main__':
    print("Starting Databot Rover Dashboard...")
    print("Access at: http://<pi-ip>:5000")
    
    # Run Flask app with SocketIO support
    # Use host='0.0.0.0' to allow external connections
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
