# flask_rover_control.py
# Enhanced rover control with live sensor data display

import time
from flask import Flask, render_template_string, jsonify, request
import RPi.GPIO as GPIO
from threading import Lock

# GPIO setup
in1, in2, en_a = 17, 27, 18
in3, in4, en_b = 5, 6, 13
GPIO.setmode(GPIO.BCM)
GPIO.setup([in1, in2, en_a, in3, in4, en_b], GPIO.OUT)
right_pwm = GPIO.PWM(en_a, 100)
left_pwm = GPIO.PWM(en_b, 100)
right_pwm.start(50)
left_pwm.start(50)

# Global variable to store latest sensor data
sensor_data = {
    "timestamp": 0,
    "temperature": 0,
    "humidity": 0,
    "co2": 0,
    "voc": 0,
    "light": 0,
    "distance_traveled": 0,
    "reverse_mode": False,
    "obstacles": {"left": 999, "front": 999, "right": 999},
    "all_sensors": {
        "front_left": 999,
        "front_center": 999,
        "front_right": 999,
        "rear_left": 999,
        "rear_center": 999,
        "rear_right": 999
    }
}
data_lock = Lock()

# --- Movement functions ---
def stop():
    GPIO.output([in1, in2, in3, in4], GPIO.LOW)

def move_forward():
    GPIO.output(in1, GPIO.HIGH)
    GPIO.output(in4, GPIO.HIGH)
    GPIO.output(in2, GPIO.LOW)
    GPIO.output(in3, GPIO.LOW)

def move_backward():
    GPIO.output(in2, GPIO.HIGH)
    GPIO.output(in3, GPIO.HIGH)
    GPIO.output(in1, GPIO.LOW)
    GPIO.output(in4, GPIO.LOW)

def move_left():
    GPIO.output(in1, GPIO.HIGH)
    GPIO.output(in3, GPIO.HIGH)
    GPIO.output(in2, GPIO.LOW)
    GPIO.output(in4, GPIO.LOW)

def move_right():
    GPIO.output(in2, GPIO.HIGH)
    GPIO.output(in4, GPIO.HIGH)
    GPIO.output(in1, GPIO.LOW)
    GPIO.output(in3, GPIO.LOW)

# --- Flask Web App ---
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Rover Control & Monitor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
      font-family: 'Segoe UI', sans-serif; 
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white; 
      padding: 20px;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    h1 { 
      text-align: center; 
      margin-bottom: 30px; 
      font-size: 2.5em;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    .dashboard { 
      display: grid; 
      grid-template-columns: 1fr 1fr; 
      gap: 20px; 
      margin-bottom: 30px;
    }
    @media (max-width: 768px) {
      .dashboard { grid-template-columns: 1fr; }
    }
    .panel {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 15px;
      padding: 20px;
      backdrop-filter: blur(10px);
    }
    .panel h2 {
      margin-bottom: 15px;
      color: #4ecca3;
      font-size: 1.3em;
    }
    .sensor-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 15px;
    }
    .sensor-item {
      background: rgba(0,0,0,0.3);
      padding: 15px;
      border-radius: 10px;
      border-left: 4px solid #4ecca3;
    }
    .sensor-label {
      font-size: 0.9em;
      color: #aaa;
      margin-bottom: 5px;
    }
    .sensor-value {
      font-size: 1.8em;
      font-weight: bold;
      color: #4ecca3;
    }
    .obstacle-indicators {
      display: flex;
      justify-content: space-around;
      margin-top: 15px;
    }
    .obstacle-box {
      text-align: center;
      padding: 15px;
      background: rgba(0,0,0,0.3);
      border-radius: 10px;
      min-width: 100px;
    }
    .obstacle-box.warning { border: 2px solid #ff6b6b; }
    .obstacle-box.safe { border: 2px solid #4ecca3; }
    .controls { 
      text-align: center;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 15px;
      padding: 30px;
      backdrop-filter: blur(10px);
    }
    .controls p {
      margin-bottom: 20px;
      color: #aaa;
    }
    button {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white; 
      border: none; 
      border-radius: 12px;
      padding: 20px; 
      margin: 10px; 
      font-size: 20px; 
      width: 100px; 
      height: 100px;
      cursor: pointer;
      transition: all 0.3s;
      box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    button:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
    button:active { 
      background: linear-gradient(135deg, #4ecca3 0%, #0fd850 100%);
      transform: translateY(0);
    }
    .button-grid { 
      display: flex; 
      flex-direction: column; 
      align-items: center; 
      margin-top: 20px; 
    }
    .row { display: flex; justify-content: center; }
    .status-bar {
      background: rgba(0,0,0,0.3);
      padding: 10px;
      border-radius: 8px;
      margin-top: 15px;
      text-align: center;
    }
    .status-indicator {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 8px;
      animation: pulse 2s infinite;
    }
    .status-indicator.active { background: #4ecca3; }
    .status-indicator.inactive { background: #666; }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🚗 Autonomous Rover Dashboard</h1>
    
    <div class="dashboard">
      <!-- Environmental Sensors Panel -->
      <div class="panel">
        <h2>📊 Environmental Sensors</h2>
        <div class="sensor-grid">
          <div class="sensor-item">
            <div class="sensor-label">Temperature</div>
            <div class="sensor-value" id="temp">--</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">Humidity</div>
            <div class="sensor-value" id="humidity">--</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">CO₂</div>
            <div class="sensor-value" id="co2">--</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">VOC</div>
            <div class="sensor-value" id="voc">--</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">Light Level</div>
            <div class="sensor-value" id="light">--</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">Distance</div>
            <div class="sensor-value" id="distance">--</div>
          </div>
        </div>
        <div class="status-bar">
          <span class="status-indicator" id="dataStatus"></span>
          <span id="lastUpdate">Waiting for data...</span>
        </div>
      </div>

      <!-- Obstacle Detection Panel -->
      <div class="panel">
        <h2>🚧 Obstacle Detection</h2>
        <div class="obstacle-indicators">
          <div class="obstacle-box" id="leftBox">
            <div class="sensor-label">← Left</div>
            <div class="sensor-value" id="obstacleLeft">--</div>
            <div style="font-size: 0.8em; margin-top: 5px;">cm</div>
          </div>
          <div class="obstacle-box" id="frontBox">
            <div class="sensor-label">↑ Front</div>
            <div class="sensor-value" id="obstacleFront">--</div>
            <div style="font-size: 0.8em; margin-top: 5px;">cm</div>
          </div>
          <div class="obstacle-box" id="rightBox">
            <div class="sensor-label">Right →</div>
            <div class="sensor-value" id="obstacleRight">--</div>
            <div style="font-size: 0.8em; margin-top: 5px;">cm</div>
          </div>
        </div>
        <div class="status-bar" style="margin-top: 20px;">
          <div style="font-size: 1.2em;" id="obstacleStatus">All Clear</div>
        </div>
      </div>
    </div>

    <!-- Control Panel -->
    <div class="controls">
      <h2 style="margin-bottom: 15px;">🎮 Manual Control</h2>
      <p>Use <strong>W / A / S / D</strong> keys or buttons below to control.<br>Release to stop.</p>
      <div class="button-grid">
        <div class="row">
          <button onmousedown="move('forward')" onmouseup="move('stop')" ontouchstart="move('forward')" ontouchend="move('stop')">↑</button>
        </div>
        <div class="row">
          <button onmousedown="move('left')" onmouseup="move('stop')" ontouchstart="move('left')" ontouchend="move('stop')">←</button>
          <button onmousedown="move('backward')" onmouseup="move('stop')" ontouchstart="move('backward')" ontouchend="move('stop')">↓</button>
          <button onmousedown="move('right')" onmouseup="move('stop')" ontouchstart="move('right')" ontouchend="move('stop')">→</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    let lastDataTime = 0;
    const OBSTACLE_THRESHOLD = 15;

    function move(cmd) { 
      fetch('/move/' + cmd); 
    }

    function updateSensorData() {
      fetch('/sensor_data')
        .then(response => response.json())
        .then(data => {
          // Update environmental sensors
          document.getElementById('temp').textContent = data.temperature.toFixed(1) + '°C';
          document.getElementById('humidity').textContent = data.humidity.toFixed(1) + '%';
          document.getElementById('co2').textContent = data.co2.toFixed(0) + ' ppm';
          document.getElementById('voc').textContent = data.voc.toFixed(0) + ' ppb';
          document.getElementById('light').textContent = data.light.toFixed(0) + ' lux';
          document.getElementById('distance').textContent = data.distance_traveled.toFixed(2) + ' m';

          // Update obstacle sensors
          const left = data.obstacles.left;
          const front = data.obstacles.front;
          const right = data.obstacles.right;

          document.getElementById('obstacleLeft').textContent = left.toFixed(1);
          document.getElementById('obstacleFront').textContent = front.toFixed(1);
          document.getElementById('obstacleRight').textContent = right.toFixed(1);

          // Update obstacle box styling
          updateObstacleBox('leftBox', left);
          updateObstacleBox('frontBox', front);
          updateObstacleBox('rightBox', right);

          // Update obstacle status
          if (front < OBSTACLE_THRESHOLD || left < OBSTACLE_THRESHOLD || right < OBSTACLE_THRESHOLD) {
            document.getElementById('obstacleStatus').textContent = '⚠️ Obstacle Detected!';
            document.getElementById('obstacleStatus').style.color = '#ff6b6b';
          } else {
            document.getElementById('obstacleStatus').textContent = '✓ All Clear';
            document.getElementById('obstacleStatus').style.color = '#4ecca3';
          }

          // Update status indicator
          const now = Date.now();
          if (now - lastDataTime > 2000) {
            document.getElementById('dataStatus').className = 'status-indicator inactive';
          } else {
            document.getElementById('dataStatus').className = 'status-indicator active';
          }
          lastDataTime = now;

          const updateTime = new Date(data.timestamp * 1000).toLocaleTimeString();
          document.getElementById('lastUpdate').textContent = 'Last update: ' + updateTime;
        })
        .catch(err => {
          console.error('Error fetching sensor data:', err);
          document.getElementById('dataStatus').className = 'status-indicator inactive';
        });
    }

    function updateObstacleBox(boxId, distance) {
      const box = document.getElementById(boxId);
      if (distance < OBSTACLE_THRESHOLD) {
        box.className = 'obstacle-box warning';
      } else {
        box.className = 'obstacle-box safe';
      }
    }

    // Keyboard controls
    let keyPressed = false;
    document.addEventListener('keydown', e => {
      if (keyPressed) return;
      const key = e.key.toLowerCase();
      if (['w','a','s','d'].includes(key)) {
        keyPressed = true;
        const cmd = {'w':'forward','a':'left','s':'backward','d':'right'}[key];
        move(cmd);
      }
    });
    
    document.addEventListener('keyup', e => {
      const key = e.key.toLowerCase();
      if (['w','a','s','d'].includes(key)) {
        keyPressed = false;
        move('stop');
      }
    });

    // Update sensor data every 500ms
    setInterval(updateSensorData, 500);
    updateSensorData(); // Initial call
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/move/<cmd>')
def move(cmd):
    commands = {
        'forward': move_forward,
        'backward': move_backward,
        'left': move_left,
        'right': move_right,
        'stop': stop
    }
    if cmd in commands:
        commands[cmd]()
    return ('', 204)

@app.route('/sensor_data')
def get_sensor_data():
    """Endpoint to retrieve latest sensor data"""
    with data_lock:
        return jsonify(sensor_data)

@app.route('/update_sensors', methods=['POST'])
def update_sensors():
    """Endpoint for main_pi.py to send sensor updates"""
    global sensor_data
    try:
        data = request.get_json()
        with data_lock:
            sensor_data.update(data)
            sensor_data['timestamp'] = time.time()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    try:
        print("Starting Rover Control Web Interface...")
        print("Access at: http://<raspberry-pi-ip>:8000")
        app.run(host='0.0.0.0', port=8000, threaded=True)
    finally:
        stop()
        GPIO.cleanup()