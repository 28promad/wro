# Databot Rover - Complete System Guide

Full autonomous navigation system with 6 ultrasonic sensors, wheel odometry, and live dashboard.

## 📁 Complete File Structure

```
rover_project/
├── rover_control.py           # Main autonomous controller ⭐
├── motor_control.py           # Motor driver interface
├── calibrate_odometry.py      # Calibration tool
├── dashboard.py               # Flask web dashboard
├── main_databot.py            # Databot firmware
├── templates/
│   └── index.html             # Dashboard UI
├── comms/
│   └── central.py             # BLE communication
└── /home/rover_logs/
    └── rover_data.db          # SQLite database
```

## 🔌 Hardware Wiring

### Ultrasonic Sensors (6x HC-SR04)

| Sensor Position | Trigger Pin | Echo Pin | BCM GPIO |
|----------------|-------------|----------|----------|
| Front Left     | 5           | 6        | GPIO 5,6 |
| Front Center   | 13          | 19       | GPIO 13,19 |
| Front Right    | 26          | 21       | GPIO 26,21 |
| Rear Left      | 17          | 27       | GPIO 17,27 |
| Rear Center    | 23          | 24       | GPIO 23,24 |
| Rear Right     | 25          | 8        | GPIO 25,8 |

**Wiring each sensor:**
- VCC → 5V (Pi pin 2 or 4)
- GND → Ground (Pi pin 6, 9, 14, 20, 25, 30, 34, 39)
- Trig → GPIO (as per table above)
- Echo → GPIO **through 1kΩ resistor** (5V to 3.3V level shift)

### L298N Motor Driver

| L298N Pin | Function | Raspberry Pi GPIO |
|-----------|----------|-------------------|
| ENA       | Left motor speed (PWM) | GPIO 7 |
| IN1       | Left motor direction 1 | GPIO 8 |
| IN2       | Left motor direction 2 | GPIO 25 |
| ENB       | Right motor speed (PWM) | GPIO 9 |
| IN3       | Right motor direction 1 | GPIO 10 |
| IN4       | Right motor direction 2 | GPIO 11 |
| 12V       | External power (7-12V) | Battery |
| GND       | Ground | Battery GND + Pi GND |
| 5V out    | 5V regulator output | Can power Pi if needed |

**Important:** Connect battery GND to Pi GND (common ground)!

### Power Supply
- **Motors**: 7-12V battery pack (recommended: 2S LiPo or 8x AA)
- **Raspberry Pi**: USB power bank or L298N 5V output
- **Databot**: Internal battery (ensure charged)

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
# On Raspberry Pi
sudo apt-get update
sudo apt-get install python3-pip python3-rpi.gpio

pip3 install flask

# Install BLE libraries (if not already installed)
pip3 install bleak
```

### 2. Enable GPIO and Bluetooth

```bash
# Add user to GPIO group
sudo usermod -a -G gpio pi

# Enable Bluetooth
sudo systemctl start bluetooth
sudo systemctl enable bluetooth
```

### 3. Calibrate Odometry

**CRITICAL STEP:** Before autonomous navigation, you must calibrate!

```bash
python3 calibrate_odometry.py
```

Follow the on-screen instructions:
1. **Measure wheel circumference** (diameter × π)
2. **Calibrate forward speed** (rover moves 5 sec, you measure distance)
3. **Calibrate turn rate** (rover turns 2 sec, you measure angle)
4. **Test with square pattern** (should return to start)

Update the values in `rover_control.py`:
```python
WHEEL_SPEED = 0.XXX          # Your calibrated value (m/s)
TURN_RATE = XX.X             # Your calibrated value (deg/s)
WHEEL_CIRCUMFERENCE = 0.XXX  # Your measured value (m)
```

### 4. Configure Tunnel Length

Edit `rover_control.py`:
```python
TUNNEL_LENGTH = 10.0  # Maximum forward distance (meters)
OBSTACLE_DIST = 15.0  # Obstacle detection threshold (cm)
```

## 🎮 Running the Rover

### Terminal 1: Start Rover Controller

```bash
python3 rover_control.py
```

**Controls:**
- **P** - Set current position as origin/start point
- **C** - Toggle between Manual and Automatic mode
- **W/↑** - Move forward (manual mode)
- **S/↓** - Move backward (manual mode)
- **A/←** - Turn left (manual mode)
- **D/→** - Turn right (manual mode)
- **SPACE** - Stop (manual mode)
- **Q** - Quit

### Terminal 2: Start Dashboard (optional)

```bash
python3 dashboard.py
```

Open browser: `http://<raspberry-pi-ip>:5000`

## 🤖 How It Works

### Navigation Modes

#### 1. Forward Mode (Default)
- Uses **front 3 ultrasonic sensors**
- Navigates autonomously toward tunnel end
- Avoids obstacles by turning left/right
- Tracks distance traveled using wheel odometry

#### 2. Reverse Mode (Auto-triggered)
- Activates when `distance_traveled >= TUNNEL_LENGTH`
- Switches to **rear 3 ultrasonic sensors**
- Navigates backward toward origin
- Uses same obstacle avoidance logic

### Wheel Odometry

Position calculation uses **speed × time**:

```python
# Forward movement
distance = WHEEL_SPEED * duration
x += distance * cos(heading)
y += distance * sin(heading)

# Turning
angle_change = TURN_RATE * duration
heading += angle_change
```

**Why not use IMU?**
- IMU accelerometer drift is severe for wheeled robots
- Double integration of acceleration accumulates massive errors
- Wheel odometry is 10-100x more accurate for short distances
- Only drawback: wheel slip (minimal on smooth surfaces)

### Obstacle Avoidance Logic

```
If CENTER sensor < threshold:
    Stop
    Turn toward side with more clearance (left vs right)

Else if LEFT sensor < threshold:
    Gently adjust right

Else if RIGHT sensor < threshold:
    Gently adjust left

Else:
    Continue forward (or backward in reverse mode)
```

## 📊 Database Schema

All sensor data and position info is logged to SQLite:

```sql
CREATE TABLE sensor_data (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    -- Air quality
    co2 REAL, voc REAL, temp REAL, hum REAL,
    -- IMU (for reference, not used for position)
    ax REAL, ay REAL, az REAL,
    gx REAL, gy REAL, gz REAL,
    -- Odometry (calculated from wheels)
    pos_x REAL,          -- X position (meters)
    pos_y REAL,          -- Y position (meters)
    yaw REAL             -- Heading (radians)
);
```

## 🔧 Troubleshooting

### Rover doesn't move
1. Check motor connections (swap IN1/IN2 if reversed)
2. Verify battery voltage (>7V under load)
3. Check common ground between Pi and L298N
4. Test motors directly: `python3 -c "from motor_control import *; m=MotorController(); m.forward(2)"`

### Ultrasonic sensors return infinity
1. Check 5V and GND connections
2. Verify GPIO pin numbers (BCM mode)
3. Ensure Echo pin has 1kΩ resistor (voltage divider)
4. Test individually: `python3 -c "from rover_control import *; setup_ultrasonic(); print(distance(5, 6))"`

### Position tracking is inaccurate
1. **Recalibrate** using `calibrate_odometry.py`
2. Check for wheel slip (use on smooth floor)
3. Verify `WHEEL_SPEED` and `TURN_RATE` values
4. Battery voltage affects motor speed (recalibrate when fresh)

### Rover doesn't avoid obstacles
1. Check `OBSTACLE_DIST` threshold (15cm default)
2. Verify sensors are facing correct direction
3. Test sensor readings: watch terminal output
4. Ensure no sensor is blocked or misaligned

### BLE connection fails
1. Ensure databot is powered on and running `main_databot.py`
2. Check Raspberry Pi Bluetooth: `bluetoothctl list`
3. Restart Bluetooth: `sudo systemctl restart bluetooth`
4. Try manual connection: `python3 -c "from comms.central import *; import asyncio; asyncio.run(BLE_UART_Central().connect())"`

### Database locked error
1. Only run ONE instance of `rover_control.py`
2. Stop dashboard before restarting controller
3. WAL mode should handle concurrent access
4. Check: `sqlite3 /home/rover_logs/rover_data.db "PRAGMA journal_mode;"`

## 🎯 Typical Mission Flow

1. **Setup**: Place rover at tunnel entrance, press **P** to set origin
2. **Start**: Rover automatically navigates forward, avoiding obstacles
3. **Forward Mode**: Uses front sensors, tracks distance
4. **Trigger**: When `distance >= TUNNEL_LENGTH`, switches to Reverse mode
5. **Reverse Mode**: Uses rear sensors, navigates back to origin
6. **Complete**: Returns to approximately starting position

## 📈 Expected Performance

| Metric | Value |
|--------|-------|
| Position accuracy | ±5-10cm per 10m travel |
| Obstacle detection range | 2-400cm (HC-SR04 spec) |
| Reaction time | ~100ms (10Hz navigation loop) |
| Database writes | Every 50 readings or 30 seconds |
| Dashboard update rate | Every 5 seconds |

## 🔬 Advanced Calibration Tips

### Wheel Speed Varies With:
- **Battery voltage**: Lower voltage = slower speed
- **Surface**: Carpet vs tile affects friction
- **Load**: Heavier rover = slower
- **Motor wear**: Calibrate periodically

**Solution**: Recalibrate when changing conditions, or implement adaptive speed sensing.

### Improving Accuracy:
1. **Encoder wheels**: Add rotary encoders for closed-loop control
2. **Compass module**: Fuse heading with magnetometer (e.g., HMC5883L)
3. **Motor PID**: Maintain constant speed despite load
4. **Path logging**: Compare odometry path to actual path, adjust calibration

## 🚨 Safety Notes

- Always test in open space first
- Keep emergency stop accessible (SPACE key or power switch)
- Monitor battery voltage (motors need >6V to work properly)
- Secure all wiring (loose wires can jam wheels)
- Test ultrasonic sensors individually before autonomous run
- Start with low speed (50-60 PWM) for testing

## 📚 Next Steps

### Enhancements to Consider:
- **GPS integration**: For outdoor navigation (real lat/lon)
- **Camera vision**: OpenCV obstacle detection and path planning
- **Lidar**: 360° scanning for better mapping
- **Multiple rovers**: Swarm coordination
- **Path planning**: A* algorithm for optimal routes
- **Web remote control**: Control rover from dashboard
- **Video streaming**: Live camera feed to dashboard

## 📝 File Quick Reference

| File | Purpose | Run on |
|------|---------|--------|
| `rover_control.py` | Main autonomous controller | Raspberry Pi |
| `motor_control.py` | Motor driver library | Imported by rover_control |
| `calibrate_odometry.py` | Calibration tool | Raspberry Pi (setup) |
| `dashboard.py` | Web visualization | Raspberry Pi (optional) |
| `main_databot.py` | Sensor firmware | Databot (separate) |

## 🆘 Getting Help

Common log messages:

- `📍 Origin set` - Current position marked as start point
- `🚧 Obstacle ahead` - Front obstacle detected, turning
- `🔄 REACHED TUNNEL END` - Switching to reverse mode
- `🎮 Control mode: MANUAL` - Manual control enabled
- `❌ DB Error` - Database write failed (check disk space)

---

**Ready to navigate! 🚀**

# CHANGED TO USING 3 FRONT ULTRASONIC SENSORS + 1 FOR REAR
