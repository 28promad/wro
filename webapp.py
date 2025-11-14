# python
# app.py
# Single-file Flask web dashboard for Databot readings

from flask import Flask, render_template_string, jsonify
import csv, os

app = Flask(__name__)

# Use relative path from the script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, "rover_logs", "data_log.csv")

# --- HTML Template (inline) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Databot Rover Dashboard</title>
<style>
body {
  font-family: Arial, sans-serif;
  background: #101820;
  color: #f4f4f4;
  text-align: center;
  padding: 20px;
}
h1 { color: #00bcd4; }
#readings {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 20px;
}
.gauge {
  width: 160px;
  height: 160px;
  background: #1a2634;
  border-radius: 50%;
  position: relative;
  box-shadow: 0 0 8px rgba(0,0,0,0.5);
}
.gauge .value {
  position: absolute;
  bottom: 10px;
  width: 100%;
  text-align: center;
  font-size: 1.2em;
}
canvas {
  width: 100%;
  height: 100%;
}
</style>
</head>
<body>
<h1>Databot Rover Live Dashboard</h1>
<div id="readings">
  <div class="gauge"><canvas id="co2"></canvas><div class="value" id="co2-val">-- ppm</div></div>
  <div class="gauge"><canvas id="tvoc"></canvas><div class="value" id="tvoc-val">-- ppb</div></div>
  <div class="gauge"><canvas id="temp"></canvas><div class="value" id="temp-val">-- °C</div></div>
  <div class="gauge"><canvas id="hum"></canvas><div class="value" id="hum-val">-- %</div></div>
</div>

<script>
async function fetchData() {
  try {
    const res = await fetch('/data');
    const data = await res.json();
    updateGauges(data);
  } catch (err) {
    console.error("Error fetching data:", err);
  }
}

// Fetch data every second
setInterval(fetchData, 1000);
// Initial fetch
fetchData();

function updateGauges(data) {
  drawGauge('co2', data.co2, 5000, 'CO₂');
  drawGauge('tvoc', data.tvoc, 1000, 'TVOC');
  drawGauge('temp', data.temp, 50, 'Temp');
  drawGauge('hum', data.hum, 100, 'Humidity');

  document.getElementById('co2-val').textContent = data.co2 + ' ppm';
  document.getElementById('tvoc-val').textContent = data.tvoc + ' ppb';
  document.getElementById('temp-val').textContent = data.temp + ' °C';
  document.getElementById('hum-val').textContent = data.hum + ' %';
}

function drawGauge(id, value, max, label) {
  const canvas = document.getElementById(id);
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  const radius = w / 2;
  const angle = (value / max) * Math.PI;
  ctx.clearRect(0, 0, w, h);

  // background arc
  ctx.beginPath();
  ctx.arc(radius, radius, radius - 10, Math.PI, 0);
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 10;
  ctx.stroke();

  // value arc
  ctx.beginPath();
  ctx.arc(radius, radius, radius - 10, Math.PI, Math.PI + angle);
  ctx.strokeStyle = '#00bcd4';
  ctx.lineWidth = 10;
  ctx.stroke();

  // label
  ctx.fillStyle = '#ccc';
  ctx.font = '16px Arial';
  ctx.textAlign = 'center';
  ctx.fillText(label, radius, h - 20);
}

// Fetch every 2 seconds
setInterval(fetchData, 2000);
fetchData();
</script>
</body>
</html>
"""

# --- Helper: Get last line from CSV and normalize keys ---
def get_latest_data():
    if not os.path.exists(CSV_FILE):
        print(f"Warning: CSV file not found at {CSV_FILE}")
        return {"co2":0,"tvoc":0,"temp":0,"hum":0}

    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            # Read all rows but only keep the last one
            last_row = None
            for row in reader:
                last_row = row
            
            if not last_row:
                return {"co2":0,"tvoc":0,"temp":0,"hum":0}

            # Normalize the data
            normalized = {}
            key_map = {
                "CO2": "co2",
                "CO₂": "co2",
                "TVOC": "tvoc",
                "Temperature": "temp",
                "Temp": "temp",
                "Humidity": "hum",
                "Hum": "hum"
            }
            
            for k, v in last_row.items():
                key = key_map.get(k.strip(), k.strip().lower())
                try:
                    normalized[key] = round(float(v), 2)
                except (ValueError, TypeError):
                    normalized[key] = 0

            # Ensure all keys exist
            for k in ["co2","tvoc","temp","hum"]:
                if k not in normalized:
                    normalized[k] = 0

            return normalized
            
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return {"co2":0,"tvoc":0,"temp":0,"hum":0}

        last = rows[-1]
        normalized = {}
        key_map = {
            "CO2": "co2",
            "CO₂": "co2",
            "TVOC": "tvoc",
            "Temperature": "temp",
            "Temp": "temp",
            "Humidity": "hum",
            "Hum": "hum"
        }
        for k, v in last.items():
            key = key_map.get(k.strip(), k.strip().lower())
            try:
                normalized[key] = round(float(v), 2)
            except:
                normalized[key] = 0

        # Ensure all keys exist
        for k in ["co2","tvoc","temp","hum"]:
            if k not in normalized:
                normalized[k] = 0

        return normalized

# --- Routes ---
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/data")
def data():
    latest = get_latest_data()
    return jsonify(latest)

# --- Run the server ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
