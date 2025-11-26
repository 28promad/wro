# rover_control.py
# Main rover controller with 6 ultrasonic sensors and wheel odometry
# Refactored to use gpiozero DistanceSensor and the gpiozero-based MotorController.

from motor_control import MotorController
import json, csv, time, os, asyncio
import sqlite3
from datetime import datetime
from collections import deque
from comms.central import BLE_UART_Central
import sys
import termios
import tty
import select
import math

# gpiozero DistanceSensor
from gpiozero import DistanceSensor

# ---------------- Configuration ----------------
LOG_DIR = "./"
DB_FILE = os.path.join(LOG_DIR, "rover_data.db")

# Tunnel and navigation parameters
TUNNEL_LENGTH = 10.0        # meters (maximum forward distance)
OBSTACLE_DIST = 20.0        # cm threshold for obstacle detection
BUFFER_SIZE = 50            # Database write buffer size
FLUSH_INTERVAL = 30.0       # seconds

# Ultrasonic sensor pin tuples remain as (trigger_pin, echo_pin) in your original naming.
# We'll construct DistanceSensor with named args: echo=<echo>, trigger=<trig>
ULTRASONIC_FRONT = {
    "front_right":   (15, 14),
    "front_center":  (23, 18),
    "front_left":    (25, 24)
}

ULTRASONIC_REAR = {
    "rear_left":     (17, 27),
    "rear_center":   (23, 24),
    "rear_right":    (25, 8)
}

# Wheel odometry parameters (CALIBRATE THESE!)
WHEEL_SPEED = 0.15          # meters per second at default motor speed
TURN_RATE = 90.0            # degrees per second during turn
WHEEL_CIRCUMFERENCE = 0.20  # meters (measure your wheel)

# Globals for gpiozero DistanceSensor objects (filled by setup_ultrasonic)
FRONT_SENSORS = {}
REAR_SENSORS = {}

# ---------------- Database Logger ----------------
class SQLiteDataLogger:
    """Handles buffered writing to SQLite database."""
    
    def __init__(self, db_path, buffer_size=50):
        self.db_path = db_path
        self.buffer_size = buffer_size
        self.buffer = deque()
        self.total_logged = 0
        self.total_flushed = 0
        self._setup_database()
    
    def _setup_database(self):
        """Create database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                co2 REAL, voc REAL, temp REAL, hum REAL,
                ax REAL, ay REAL, az REAL,
                gx REAL, gy REAL, gz REAL,
                pos_x REAL, pos_y REAL, yaw REAL
            );
            CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp);
            CREATE INDEX IF NOT EXISTS idx_position ON sensor_data(pos_x, pos_y);
        """)
        
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.commit()
        conn.close()
    
    def add(self, data):
        """Add data to buffer (non-blocking)."""
        timestamp = datetime.now().isoformat()
        entry = (
            timestamp,
            data.get('co2'), data.get('voc'), data.get('temp'), data.get('hum'),
            data.get('ax'), data.get('ay'), data.get('az'),
            data.get('gx'), data.get('gy'), data.get('gz'),
            data.get('pos_x'), data.get('pos_y'), data.get('yaw')
        )
        self.buffer.append(entry)
        self.total_logged += 1
    
    def flush(self):
        """Write all buffered data to database."""
        if not self.buffer:
            return 0
        
        entries = list(self.buffer)
        self.buffer.clear()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO sensor_data 
                (timestamp, co2, voc, temp, hum, ax, ay, az, gx, gy, gz, pos_x, pos_y, yaw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, entries)
            conn.commit()
            conn.close()
            
            self.total_flushed += len(entries)
            return len(entries)
        except Exception as e:
            print(f"❌ DB Error: {e}")
            self.buffer.extend(entries)
            return 0
    
    def should_flush(self):
        return len(self.buffer) >= self.buffer_size

# ---------------- Odometry Calculator ----------------
class Odometry:
    """Calculate position using wheel odometry (speed × time)."""
    
    def __init__(self, wheel_speed=0.15, turn_rate=90.0):
        self.wheel_speed = wheel_speed  # m/s
        self.turn_rate = turn_rate      # deg/s
        
        # Current state
        self.x = 0.0          # meters
        self.y = 0.0          # meters
        self.heading = 0.0    # degrees (0 = forward)
        
        # Start position (for return navigation)
        self.start_x = 0.0
        self.start_y = 0.0
    
    def set_origin(self):
        """Set current position as the origin/start point."""
        self.start_x = self.x
        self.start_y = self.y
        print(f"📍 Origin set at ({self.x:.2f}, {self.y:.2f})")
    
    def update_forward(self, duration):
        """Update position after moving forward."""
        distance = self.wheel_speed * duration
        rad = math.radians(self.heading)
        self.x += distance * math.cos(rad)
        self.y += distance * math.sin(rad)
    
    def update_backward(self, duration):
        """Update position after moving backward."""
        distance = self.wheel_speed * duration
        rad = math.radians(self.heading)
        self.x -= distance * math.cos(rad)
        self.y -= distance * math.sin(rad)
    
    def update_turn_left(self, duration):
        """Update heading after turning left."""
        angle_change = self.turn_rate * duration
        self.heading += angle_change
        self.heading %= 360  # Keep between 0-360
    
    def update_turn_right(self, duration):
        """Update heading after turning right."""
        angle_change = self.turn_rate * duration
        self.heading -= angle_change
        self.heading %= 360
    
    def distance_from_start(self):
        """Calculate straight-line distance from start position."""
        dx = self.x - self.start_x
        dy = self.y - self.start_y
        return math.sqrt(dx**2 + dy**2)
    
    def get_position(self):
        """Return current position dict."""
        return {
            'pos_x': self.x,
            'pos_y': self.y,
            'yaw': math.radians(self.heading),  # Convert to radians for consistency
            'distance_traveled': self.distance_from_start()
        }

# ---------------- Ultrasonic Sensor Setup (gpiozero) ----------------
def setup_ultrasonic():
    """Initialize all 6 ultrasonic sensors as gpiozero DistanceSensor objects."""
    global FRONT_SENSORS, REAR_SENSORS

    # Helper to instantiate DistanceSensor safely
    def make_sensor(trig_pin, echo_pin, max_distance_m=4.0):
        try:
            # Named args to be explicit: DistanceSensor(echo=<echo>, trigger=<trigger>)
            return DistanceSensor(echo=echo_pin, trigger=trig_pin, max_distance=max_distance_m, queue_len=3)
        except Exception as e:
            print(f"⚠ Failed to create DistanceSensor (trig={trig_pin}, echo={echo_pin}): {e}")
            return None

    # Build sensor objects from configuration constants
    FRONT_SENSORS = {}
    for name, (trig, echo) in ULTRASONIC_FRONT.items():
        FRONT_SENSORS[name] = make_sensor(trig, echo)

    REAR_SENSORS = {}
    for name, (trig, echo) in ULTRASONIC_REAR.items():
        REAR_SENSORS[name] = make_sensor(trig, echo)

    print("✓ 6 gpiozero ultrasonic sensors initialized (objects may be None if initialization failed)")

def get_sensor_readings(use_rear=False):
    """Read either front or rear ultrasonic sensors in cm."""
    sensors = REAR_SENSORS if use_rear else FRONT_SENSORS
    readings = {}

    for pos, sensor in sensors.items():
        if sensor is None:
            readings[pos] = float('inf')
            continue

        try:
            # DistanceSensor.distance returns meters (float between 0..max_distance)
            val_m = sensor.distance
            if val_m is None:
                readings[pos] = float('inf')
            else:
                readings[pos] = val_m * 100.0  # meters -> cm
        except Exception as e:
            # Catch runtime errors (e.g., sensor unplugged)
            readings[pos] = float('inf')

    return readings

# ---------------- Navigation Logic ----------------
class Navigator:
    """Handles autonomous navigation with obstacle avoidance."""
    
    def __init__(self, motor, odometry, tunnel_length=10.0, obstacle_dist=15.0):
        self.motor = motor
        self.odometry = odometry
        self.tunnel_length = tunnel_length
        self.obstacle_dist = obstacle_dist
        
        self.reverse_mode = False
        self.manual_mode = True # start up in manual mode
        self.running = False
        self.log = []
        self.inverse_log = []
    
    def toggle_manual(self):
        """Toggle between manual and automatic control."""
        self.manual_mode = not self.manual_mode
        mode = "MANUAL" if self.manual_mode else "AUTOMATIC"
        print(f"🎮 Control mode: {mode}")
        if self.manual_mode:
            self.motor.stop()
            self.log = [] # Reset the log of turns & times
        else:
            self.inverse_log = [] # Reset the inverse log
    
    def check_distance_limit(self):
        """Check if rover has reached tunnel length limit."""
        dist = self.odometry.distance_from_start()
        
        # Reached end of tunnel
        if not self.reverse_mode and dist >= self.tunnel_length:
            print(f"\n🔄 REACHED TUNNEL END ({dist:.2f}m)")
            print("Switching to REVERSE mode - using rear sensors")
            self.reverse_mode = True

            # Build inverse log for return journey
            temp = []
            for e in self.log:
                if e[0] == 'left':
                    temp.append(['right', e[1]])
                elif e[0] == 'right':
                    temp.append(['left', e[1]])
                else:
                    temp.append(e)

            self.inverse_log = []
            for i in range(len(temp), 0, -1):
                self.inverse_log.append(temp[i-1])

            # Brief stop, then start return journey
            self.motor.stop()
            time.sleep(0.5)
            return True
        
        return False
    
    
    def automated_return(self):
        """ automated navigation for return back to origin """
        for action, duration in self.inverse_log:
            if action != 'forward':
                if action == 'left':
                    print(f"Returning: TURN LEFT for {duration:.2f}s")
                    self.motor.turn_left(duration)
                    self.odometry.update_turn_left(duration)
                elif action == 'right':
                    print(f"Returning: TURN RIGHT for {duration:.2f}s")
                    self.motor.turn_right(duration)
                    self.odometry.update_turn_right(duration)
            else:
                print(f"Returning: MOVE FORWARD for {duration:.2f}s")
                self.motor.forward(duration)
                self.odometry.update_forward(duration)

        self.reverse_mode = not self.reverse_mode
        self.motor.stop()
        print("REACHED ORIGIN. Switched to MANUAL mode.")
    
    def navigate_step(self):
        """Execute one navigation step (obstacle avoidance). Keeping a log of turns and durations."""
        if self.manual_mode:
            return  # Don't navigate in manual mode
        
        # Check if we've reached the distance limit
        if self.check_distance_limit():
            return
        
        # Read appropriate sensors (use rear sensors when reverse_mode True)
        readings = get_sensor_readings(use_rear=self.reverse_mode)
        
        # If sensors missing keys, fall back to using front sensors
        left = readings.get('front_left', float('inf'))
        center = readings.get('front_center', float('inf'))
        right = readings.get('front_right', float('inf'))

        if self.reverse_mode:
            # When in reverse mode prefer rear sensors if available
            left = readings.get('rear_left', left)
            center = readings.get('rear_center', center)
            right = readings.get('rear_right', right)

        # Obstacle avoidance logic
        if center < self.obstacle_dist:
            self.motor.stop()
            time.sleep(0.1)
            
            # Decide which way to turn
            if left > right:
                print(f"🚧 Obstacle ahead, turning LEFT (L:{left:.1f} R:{right:.1f})")
                duration = 0.4
                self.motor.turn_left(duration)
                self.odometry.update_turn_left(duration)
                self.log.append(('left', duration))
            else:
                print(f"🚧 Obstacle ahead, turning RIGHT (L:{left:.1f} R:{right:.1f})")
                duration = 0.4
                self.motor.turn_right(duration)
                self.odometry.update_turn_right(duration)
                self.log.append(('right', duration))

        # Turning right if obstacle on left
        elif left < self.obstacle_dist:
            print(f"🚧 Obstacle on left ({left:.1f}cm), adjusting RIGHT")
            self.motor.set_speed(60)
            duration = 0.2
            self.log.append(('right', duration))
            self.motor.turn_right(duration)
            self.odometry.update_turn_right(duration)
            self.motor.set_speed(75)
        
        # Turning left if obstacle on right
        elif right < self.obstacle_dist:
            print(f"🚧 Obstacle on right ({right:.1f}cm), adjusting LEFT")
            self.motor.set_speed(60)
            duration = 0.2
            self.log.append(('left', duration))
            self.motor.turn_left(duration)
            self.odometry.update_turn_left(duration)
            self.motor.set_speed(75)
        
        else:
            # No obstacles - move in current direction
            if self.reverse_mode:
                # Moving backward toward start
                self.motor.backward()
            else:
                # Moving forward into tunnel
                duration = 0.2
                self.log.append(('forward', duration))
                self.motor.forward(duration)

# ---------------- Keyboard Input Handler ----------------
class KeyboardInput:
    """Non-blocking keyboard input for manual control."""
    
    def __init__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    
    def get_key(self):
        """Get a key press without blocking."""
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None
    
    def cleanup(self):
        """Restore terminal settings."""
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

# ---------------- Main Async Loop ----------------
async def main():
    """Main control loop."""
    # Initialize components
    motor = MotorController()
    odometry = Odometry(WHEEL_SPEED, TURN_RATE)
    navigator = Navigator(motor, odometry, TUNNEL_LENGTH, OBSTACLE_DIST)
    logger = SQLiteDataLogger(DB_FILE, BUFFER_SIZE)
    keyboard = KeyboardInput()
    
    # BLE setup
    central = BLE_UART_Central()
    data_queue = asyncio.Queue()
    
    def handle_databot_rx(raw):
        try:
            text = raw.decode('utf-8')
            data = json.loads(text)
            asyncio.get_event_loop().call_soon_threadsafe(data_queue.put_nowait, data)
        except Exception:
            pass
    
    central.on_receive(handle_databot_rx)
    
    print("\n" + "="*60)
    print("🤖 DATABOT ROVER - AUTONOMOUS NAVIGATION (gpiozero)")
    print("="*60)
    print("Controls:")
    print("  P - Set current position as origin")
    print("  C - Toggle Manual/Automatic mode")
    print("  W/↑ - Forward    S/↓ - Backward")
    print("  A/← - Left       D/→ - Right")
    print("  SPACE - Stop     Q - Quit")
    print("="*60 + "\n")
    
    setup_ultrasonic()
    
    # Connect to databot with retry
    print("Connecting to databot...")
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"Attempt {attempt}/{max_attempts}...")
        
        try:
            if await asyncio.wait_for(central.connect(), timeout=10.0):
                await central.send('Start')
                await asyncio.sleep(1)
                print("✓ Connected to databot\n")
                break
        except asyncio.TimeoutError:
            print(f"Connection timeout, retrying...")
        except Exception as e:
            print(f"Connection error: {e}")
        
        if attempt < max_attempts:
            await asyncio.sleep(3)
    else:
        print("❌ Failed to connect after multiple attempts")
        print("⚠️  Continuing without databot (position tracking only)")
        print("")
    
    # Timing
    last_flush = time.time()
    last_nav = time.time()
    last_status = time.time()
    
    try:
        while True:
            current_time = time.time()
            
            # Handle keyboard input
            key = keyboard.get_key()
            if key:
                if key.lower() == 'q':
                    print("\n👋 Quitting...")
                    break
                elif key.lower() == 'p':
                    odometry.set_origin()
                elif key.lower() == 'c':
                    navigator.toggle_manual()
                elif navigator.manual_mode:
                    # Manual control
                    if key in ['w', '\x1b[A']:  # W or Up arrow
                        motor.forward()
                        odometry.update_forward(0.1)
                        print("⬆️ Forward")
                    elif key in ['s', '\x1b[B']:  # S or Down arrow
                        motor.backward()
                        odometry.update_backward(0.1)
                        print("⬇️ Backward")
                    elif key in ['a', '\x1b[D']:  # A or Left arrow
                        motor.turn_left(0.1)
                        odometry.update_turn_left(0.1)
                        print("⬅️ Left")
                    elif key in ['d', '\x1b[C']:  # D or Right arrow
                        motor.turn_right(0.1)
                        odometry.update_turn_right(0.1)
                        print("➡️ Right")
                    elif key == ' ':
                        motor.stop()
                        print("⏸️ Stop")
            
            # Navigation (if in automatic mode)
            if not navigator.manual_mode and current_time - last_nav > 0.1:
                navigator.navigate_step()
                
                # Update odometry based on movement
                if motor._is_moving:
                    odometry.update_forward(0.1)
                
                last_nav = current_time
            
            # Process databot sensor data
            try:
                data = data_queue.get_nowait()
                
                # Add odometry data to sensor data
                data.update(odometry.get_position())
                logger.add(data)
                
            except asyncio.QueueEmpty:
                pass
            
            # Flush database
            if logger.should_flush() or (current_time - last_flush >= FLUSH_INTERVAL):
                flushed = logger.flush()
                if flushed > 0:
                    last_flush = current_time
            
            # Status updates
            if current_time - last_status > 5.0:
                pos = odometry.get_position()
                mode = "REVERSE" if navigator.reverse_mode else "FORWARD"
                control = "MANUAL" if navigator.manual_mode else "AUTO"
                print(f"📊 [{control}/{mode}] Pos: ({pos['pos_x']:.2f}, {pos['pos_y']:.2f}) "
                      f"Heading: {odometry.heading:.1f}° Distance: {pos['distance_traveled']:.2f}m")
                last_status = current_time
            
            await asyncio.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted!")
    finally:
        # Cleanup
        motor.stop()
        logger.flush()
        keyboard.cleanup()
        # gpiozero device cleanup is automatic on program exit; if you want to be explicit:
        try:
            for s in list(FRONT_SENSORS.values()) + list(REAR_SENSORS.values()):
                if s is not None:
                    s.close()
        except Exception:
            pass
        
        if central.is_connected:
            await central.disconnect()
        
        print("\n✓ Shutdown complete")

# ---------------- Entry Point ----------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Stopped")
