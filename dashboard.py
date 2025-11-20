# dashboard.py
# Flask dashboard for visualizing rover data from SQLite database

from flask import Flask, render_template, jsonify, request
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuration
LOG_DIR = "./"
DB_FILE = os.path.join(LOG_DIR, "rover_data.db")

# ---------------- Database Helper Functions ----------------
def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def get_latest_data(limit=100):
    """Get the most recent sensor readings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sensor_data 
        ORDER BY id DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convert to list of dicts
    return [dict(row) for row in rows]

def get_data_range(start_time=None, end_time=None, limit=1000):
    """Get data within a specific time range."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if start_time and end_time:
        cursor.execute("""
            SELECT * FROM sensor_data 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY id DESC
            LIMIT ?
        """, (start_time, end_time, limit))
    else:
        cursor.execute("""
            SELECT * FROM sensor_data 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_stats():
    """Get overall statistics from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total rows
    cursor.execute("SELECT COUNT(*) as count FROM sensor_data")
    total_rows = cursor.fetchone()['count']
    
    # Time range
    cursor.execute("""
        SELECT 
            MIN(timestamp) as first_entry,
            MAX(timestamp) as last_entry
        FROM sensor_data
    """)
    time_range = dict(cursor.fetchone())
    
    # Average values
    cursor.execute("""
        SELECT 
            AVG(co2) as avg_co2,
            AVG(voc) as avg_voc,
            AVG(temp) as avg_temp,
            AVG(hum) as avg_hum,
            AVG(incline) as avg_incline,
            MAX(co2) as max_co2,
            MAX(temp) as max_temp,
            MAX(incline) as max_incline
        FROM sensor_data
        WHERE timestamp > datetime('now', '-1 hour')
    """)
    averages = dict(cursor.fetchone())
    
    # Database size
    db_size_mb = os.path.getsize(DB_FILE) / (1024 * 1024)
    
    conn.close()
    
    return {
        'total_rows': total_rows,
        'first_entry': time_range['first_entry'],
        'last_entry': time_range['last_entry'],
        'db_size_mb': round(db_size_mb, 2),
        'averages': averages
    }

def get_path_data(limit=500):
    """Get position data for mapping the rover's path."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, pos_x, pos_y, yaw
        FROM sensor_data
        WHERE pos_x IS NOT NULL AND pos_y IS NOT NULL
        ORDER BY id ASC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# ---------------- Flask Routes ----------------
@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')

@app.route('/api/latest')
def api_latest():
    """API endpoint for latest data."""
    limit = request.args.get('limit', 100, type=int)
    data = get_latest_data(limit)
    return jsonify(data)

@app.route('/api/range')
def api_range():
    """API endpoint for data within a time range."""
    start = request.args.get('start')
    end = request.args.get('end')
    limit = request.args.get('limit', 1000, type=int)
    
    data = get_data_range(start, end, limit)
    return jsonify(data)

@app.route('/api/stats')
def api_stats():
    """API endpoint for overall statistics."""
    stats = get_stats()
    return jsonify(stats)

@app.route('/api/path')
def api_path():
    """API endpoint for rover path data."""
    limit = request.args.get('limit', 500, type=int)
    path = get_path_data(limit)
    return jsonify(path)

@app.route('/api/live')
def api_live():
    """API endpoint for real-time data (last 30 seconds)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sensor_data 
        WHERE timestamp > datetime('now', '-30 seconds')
        ORDER BY id DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])

# ---------------- Main Entry Point ----------------
if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists(DB_FILE):
        print(f"⚠ Warning: Database not found at {DB_FILE}")
        print("Make sure main_pi.py has been run at least once.")
    
    print("\n" + "="*60)
    print("DATABOT ROVER DASHBOARD")
    print("="*60)
    print(f"Database: {DB_FILE}")
    print("Starting Flask server...")
    print("="*60 + "\n")
    
    # Run Flask app
    # Use host='0.0.0.0' to make it accessible from other devices on the network
    app.run(host='0.0.0.0', port=5000, debug=True)