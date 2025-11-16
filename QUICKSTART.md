# Quick Start Guide - Databot Rover Dashboard

## 30-Second Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start Rover Controller (Terminal 1)
```bash
python main_pi.py
```

### Step 3: Start Web Dashboard (Terminal 2)
```bash
python web_app.py
```

### Step 4: Open Dashboard
- Find your Raspberry Pi IP: `hostname -I`
- Open browser: `http://<pi-ip>:5000`

## What You'll See

✅ **Real-time Environmental Data:**
- CO₂ level (ppm)
- TVOC (ppb)  
- Temperature (°C)
- Humidity (%)

✅ **Rover Kinematics:**
- Position X, Y (meters)
- Heading/Yaw (degrees)

✅ **Live Graphs:**
- Environmental trends
- IMU acceleration (ax, ay, az)
- Gyroscope data (gx, gy, gz)
- 2D path on XY map

✅ **Status:**
- Connection indicator (🟢 Connected / 🔴 Disconnected)
- Last update timestamp
- Total data points collected

## Key Points

💡 **Always Running**: Rover keeps moving even if databot disconnects

💡 **No CSV Bottleneck**: Real-time data in memory, async CSV logging

💡 **Multi-Client**: Multiple browsers can view dashboard simultaneously

💡 **Responsive**: Updates every 50ms for IMU, 1 second for sensors

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Page won't load | Check if `web_app.py` is running |
| Data not updating | Verify `main_pi.py` is running and databot is connected |
| Can't find Pi IP | Run `hostname -I` on the Raspberry Pi |
| High CPU usage | Increase sleep time in main_pi.py (line ~176) |

## Next Steps

1. **Customize Dashboard**: Edit colors/labels in `templates/dashboard.html`
2. **Add More Sensors**: Add fields to `rover_data_service.py`
3. **Monitor from External Network**: Configure firewall (port 5000)
4. **Set Auto-Start**: Create systemd service (see DASHBOARD_README.md)

---

Enjoy real-time rover monitoring! 🤖
