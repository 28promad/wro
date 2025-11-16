# Databot Rover Real-Time Dashboard

A real-time web dashboard for monitoring the Databot rover with live sensor visualization, graphs, and telemetry data. This system separates the data acquisition layer from the presentation layer for better performance and reliability.

## Architecture Overview

```
main_pi.py (Rover Control + Sensor Reader)
    ↓
rover_data_service.py (Shared In-Memory Data Buffer)
    ↓
web_app.py (Flask Web Server)
    ↓
dashboard.html (WebSocket-Connected Browser Client)
```

### Key Features

✅ **Real-Time Updates**: WebSocket-based live data streaming (50Hz from IMU, 1Hz from sensors)
✅ **Always Running**: `main_pi.py` continues operating even when databot is disconnected
✅ **Responsive UI**: Beautiful dashboard with live graphs and status indicators
✅ **Efficient Data Handling**: In-memory circular buffer prevents CSV I/O bottlenecks
✅ **Historical Logging**: Optional CSV logging for AI training data (async, non-blocking)
✅ **Multi-Client Support**: Multiple browsers can connect simultaneously
✅ **Low Latency**: Data reaches dashboard within 50ms of acquisition

## Setup & Installation

### 1. Install Dependencies

On the Raspberry Pi:

```bash
pip install -r requirements.txt
```

### 2. File Structure

Make sure these files exist:

```
.
├── main_pi.py                    # Main rover controller (run this)
├── web_app.py                    # Flask web server (run this)
├── rover_data_service.py         # Shared data buffer
├── requirements.txt              # Python dependencies
├── motor_control.py              # Motor control module
├── comms/
│   └── central.py                # BLE communication
├── templates/
│   └── dashboard.html            # Web UI
└── rover_logs/                   # CSV logs (auto-created)
```

### 3. Start the Rover System

On the Raspberry Pi, open two terminals:

**Terminal 1 - Start Main Rover Controller:**
```bash
python main_pi.py
```

**Terminal 2 - Start Web Dashboard:**
```bash
python web_app.py
```

The web server will output:
```
Starting Databot Rover Dashboard...
Access at: http://<pi-ip>:5000
```

### 4. Access the Dashboard

From any computer on the network:
- Open browser: `http://<raspberry-pi-ip>:5000`
- Example: `http://192.168.1.100:5000`

## How It Works

### Data Flow

1. **Acquisition** (`main_pi.py`)
   - Reads IMU at 50Hz (from `update_kinematics()`)
   - Reads sensors from databot at 1Hz (when connected)
   - Reads ultrasonic sensors in real-time
   - Never blocks waiting for databot connection

2. **Storage** (`rover_data_service.py`)
   - Maintains in-memory circular buffer (default: 300 readings)
   - Thread-safe access for multi-process updates
   - Optional callbacks for real-time listeners
   - CSV logging happens asynchronously

3. **Streaming** (`web_app.py`)
   - Flask server exposes REST APIs
   - WebSocket connection for real-time updates
   - Emits data to all connected clients
   - No polling needed - push-based updates

4. **Display** (`dashboard.html`)
   - Connects via WebSocket
   - Updates charts in real-time
   - Shows status indicators
   - Displays kinematics (position, heading)

### What Happens When Databot Disconnects?

✅ `main_pi.py` **continues running**:
- Still reads ultrasonic sensors
- Still performs obstacle avoidance
- Still logs locally to CSV
- Still updates the data service

✅ Web dashboard **stays responsive**:
- Shows last known sensor values
- Displays "Disconnected" status
- Continues showing rover's local sensor data (ultrasonic)
- Waits for reconnection

### What Data Is Logged?

#### In-Memory (Real-Time Dashboard)
- CO₂, VOC, Temperature, Humidity
- Accelerometer (ax, ay, az)
- Gyroscope (gx, gy, gz)
- Position (pos_x, pos_y)
- Heading (yaw)
- Connection status & timestamp

#### CSV File (Optional)
- Same fields as above
- Logged to `rover_logs/data_log.csv`
- Useful for training AI models
- Non-blocking I/O

## Configuration

### In `rover_data_service.py`

```python
# Adjust circular buffer size (for 50Hz IMU + 1Hz sensors)
service = RoverDataService(max_history=300)  # ~6 seconds of history
```

### In `main_pi.py`

```python
# CSV logging directory
LOG_DIR = "/home/pi/rover_logs"

# Obstacle detection threshold
OBSTACLE_DIST = 15.0  # cm
```

### In `web_app.py`

```python
# Web server host and port
socketio.run(app, host='0.0.0.0', port=5000, debug=True)

# Change to debug=False in production
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| IMU Update Rate | 50 Hz |
| Sensor Reading Rate | 1 Hz |
| Data Service Latency | < 1 ms |
| WebSocket Latency | 10-50 ms (network dependent) |
| In-Memory Buffer Size | ~300 readings (~10 KB) |
| CSV I/O Time | Async (non-blocking) |

## API Endpoints

### REST Endpoints

| Endpoint | Method | Response |
|----------|--------|----------|
| `/` | GET | Dashboard HTML |
| `/api/current` | GET | Latest sensor data |
| `/api/history?limit=100` | GET | Historical readings |
| `/api/graphs?limit=100` | GET | Time-series graph data |
| `/api/status` | GET | Connection status |

### WebSocket Events

**Client → Server:**
- `request_graph_data` - Request graph data (payload: `{limit: 100}`)
- `request_status` - Request status update

**Server → Client:**
- `update` - New sensor data (emitted automatically)
- `graph_data` - Graph data response
- `status_update` - Status update response

## Troubleshooting

### Dashboard Shows "Disconnected" But Rover Is Connected

Check the BLE connection in `main_pi.py`:
```python
central.is_connected  # Should be True when databot is connected
```

### High CPU Usage

The websocket updates might be too frequent. Adjust in `main_pi.py`:
```python
await asyncio.sleep(0.05)  # Increase this value to 0.1 for 10Hz instead of 20Hz
```

### CSV File Growing Too Large

The system now uses in-memory buffering primarily. CSV is optional. To disable:

In `main_pi.py`, modify `log_data()`:
```python
def log_data(data):
    service = get_service()
    service.update(data)
    # Remove or comment out the CSV writing section
```

### WebSocket Connection Issues

1. Check firewall allows port 5000
2. Ensure Flask is running: `python web_app.py`
3. Try accessing dashboard from different network device
4. Check logs for CORS issues

## Development & Customization

### Add More Sensors

1. Update `rover_data_service.py` - Add fields to `current_data` dict
2. Update `main_pi.py` - Read sensor and call `service.update(data)`
3. Update `dashboard.html` - Add card in sensors-grid or new chart

### Modify Dashboard Styling

All styles are in `templates/dashboard.html` in the `<style>` tag. Main colors:

- Primary: `#00d4ff` (cyan)
- Success: `#00ff99` (green)
- Warning: `#ff8800` (orange)
- Danger: `#ff4444` (red)

### Add New Charts

In `dashboard.html`:

1. Add canvas: `<canvas id="my-chart"></canvas>`
2. Initialize in `initializeCharts()`:
   ```javascript
   charts.my = new Chart(document.getElementById('my-chart'), { ... });
   ```
3. Update in `updateCharts()`:
   ```javascript
   if (graphData.myField && charts.my) {
       // Update chart data
       charts.my.update('none');
   }
   ```

## Deployment Considerations

### Production Checklist

- [ ] Disable Flask debug mode: `debug=False`
- [ ] Use HTTPS with SSL certificate
- [ ] Add authentication for dashboard access
- [ ] Configure firewall to restrict port 5000
- [ ] Set up systemd service for auto-start
- [ ] Monitor CSV file size (implement cleanup)
- [ ] Set up logging to file

### Systemd Service Example

Create `/etc/systemd/system/rover-dashboard.service`:

```ini
[Unit]
Description=Databot Rover Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rover
ExecStart=/usr/bin/python3 /home/pi/rover/web_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable rover-dashboard
sudo systemctl start rover-dashboard
```

## FAQ

**Q: Does the rover stop if the dashboard crashes?**
A: No. `main_pi.py` and the rover operate independently. The dashboard is just for monitoring.

**Q: Can I access the dashboard from outside my network?**
A: Yes, but ensure proper firewall configuration. Consider adding authentication first.

**Q: How long is data stored?**
A: In-memory: ~6 seconds (300 readings). CSV: indefinite (until manually deleted).

**Q: Can I reduce memory usage?**
A: Yes, adjust `RoverDataService(max_history=100)` for shorter history.

**Q: Does CSV logging impact performance?**
A: No, it's async and non-blocking with the new implementation.

## License

Part of the Databot Rover WRO project.

## Support

For issues or questions, check:
1. `main_pi.py` console for rover errors
2. `web_app.py` console for server errors
3. Browser console (F12) for frontend errors
4. Flask debug output for API issues
