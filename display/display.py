from flask import Flask, render_template_string, jsonify
import random

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Databot Rover Live Dashboard</title>
    <style>
        body {
            background-color: #0f1c2e;
            color: #fff;
            font-family: Arial, sans-serif;
            text-align: center;
            padding-top: 50px;
        }
        h1 {
            margin-bottom: 40px;
        }
        .gauge-container {
            display: flex;
            justify-content: center;
            gap: 40px;
        }
        .gauge {
            background-color: #1e2a3a;
            border-radius: 10px;
            padding: 20px;
            width: 150px;
            box-shadow: 0 0 10px #000;
        }
        .label {
            font-size: 1.2em;
            margin-bottom: 10px;
        }
        .value {
            font-size: 2em;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>Databot Rover Live Dashboard</h1>
    <div class="gauge-container">
        <div class="gauge">
            <div class="label">CO₂</div>
            <div class="value" id="co2">-- ppm</div>
        </div>
        <div class="gauge">
            <div class="label">Humidity</div>
            <div class="value" id="humidity">-- %</div>
        </div>
        <div class="gauge">
            <div class="label">Temperature</div>
            <div class="value" id="temperature">-- °C</div>
        </div>
        <div class="gauge">
            <div class="label">TVOC</div>
            <div class="value" id="tvoc">-- ppb</div>
        </div>
    </div>

    <script>
        function updateData() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('co2').textContent = data.co2 + ' ppm';
                    document.getElementById('humidity').textContent = data.humidity + ' %';
                    document.getElementById('temperature').textContent = data.temperature + ' °C';
                    document.getElementById('tvoc').textContent = data.tvoc + ' ppb';
                });
        }

        setInterval(updateData, 2000); // Update every 2 seconds
        updateData(); // Initial load
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def data():
    sensor_data = {
        'co2': round(random.uniform(390, 410), 1),        # ppm
        'humidity': round(random.uniform(20, 50), 1),     # %
        'temperature': round(random.uniform(24, 30), 1),  # °C
        'tvoc': int(random.uniform(0, 5))            # ppb
    }
    return jsonify(sensor_data)

if __name__ == '__main__':
    app.run(debug=True)
