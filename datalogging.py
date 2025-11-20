# main_pi.py
# Raspberry Pi data logger for Databot with auto-reconnect
# Now uses IMU data for heading and tilt calculations

import asyncio
import json
import sqlite3
import time
import os
from datetime import datetime
from collections import deque
from comms.central import BLE_UART_Central
import math

# ---------------- Configuration ----------------
LOG_DIR = "./"
DB_FILE = os.path.join(LOG_DIR, "rover_data.db")

# Buffer configuration
BUFFER_SIZE = 50           # Write to DB every 50 entries
FLUSH_INTERVAL = 1.0      # Or every 1 seconds

# Reconnection configuration
RECONNECT_DELAY = 5.0      # Seconds to wait before reconnect attempt
MAX_RECONNECT_ATTEMPTS = 0 # 0 = infinite retries
CONNECTION_TIMEOUT = 10.0  # Seconds to wait for connection

# IMU calibration - complementary filter
COMP_FILTER_ALPHA = 0.98   # 98% gyro, 2% accel

# ---------------- Database Schema ----------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    co2 REAL,
    voc REAL,
    temp REAL,
    hum REAL,
    ax REAL,
    ay REAL,
    az REAL,
    gx REAL,
    gy REAL,
    gz REAL,
    pos_x REAL,
    pos_y REAL,
    yaw REAL,
    pitch REAL,
    roll REAL,
    incline REAL
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_position ON sensor_data(pos_x, pos_y);
"""

# ---------------- IMU Data Processor ----------------
class IMUProcessor:
    """Process IMU data for heading, pitch, roll, and incline."""
    
    def __init__(self):
        self.pitch = 0.0      # Pitch angle (radians)
        self.roll = 0.0       # Roll angle (radians)
        self.yaw = 0.0        # Yaw/heading (radians)
        self.last_update = time.time()
    
    def update(self, ax, ay, az, gx, gy, gz):
        """
        Update orientation using complementary filter.
        
        Args:
            ax, ay, az: Accelerometer readings (m/s^2 or g)
            gx, gy, gz: Gyroscope readings (rad/s)
        
        Returns:
            dict with pitch, roll, yaw, incline
        """
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        if dt <= 0 or dt > 1.0:  # Ignore bad time deltas
            dt = 0.02
        
        # --- Pitch from accelerometer (stable but noisy) ---
        try:
            pitch_accel = math.atan2(ax, math.sqrt(ay**2 + az**2))
        except (ValueError, ZeroDivisionError):
            pitch_accel = self.pitch
        
        # --- Roll from accelerometer ---
        try:
            roll_accel = math.atan2(ay, math.sqrt(ax**2 + az**2))
        except (ValueError, ZeroDivisionError):
            roll_accel = self.roll
        
        # --- Integrate gyroscope (fast but drifts) ---
        pitch_gyro = self.pitch + gy * dt
        roll_gyro = self.roll + gx * dt
        yaw_gyro = self.yaw + gz * dt
        
        # --- Complementary filter: fuse accel + gyro ---
        self.pitch = (COMP_FILTER_ALPHA * pitch_gyro) + ((1.0 - COMP_FILTER_ALPHA) * pitch_accel)
        self.roll = (COMP_FILTER_ALPHA * roll_gyro) + ((1.0 - COMP_FILTER_ALPHA) * roll_accel)
        self.yaw = yaw_gyro  # No magnetometer, so yaw drifts (for now)
        
        # Normalize yaw to [-pi, pi]
        while self.yaw > math.pi:
            self.yaw -= 2 * math.pi
        while self.yaw < -math.pi:
            self.yaw += 2 * math.pi
        
        # --- Calculate incline (total tilt from horizontal) ---
        incline = math.sqrt(self.pitch**2 + self.roll**2)
        
        return {
            'pitch': self.pitch,           # radians
            'roll': self.roll,             # radians
            'yaw': self.yaw,               # radians
            'incline': incline,            # radians
            'pitch_deg': math.degrees(self.pitch),
            'roll_deg': math.degrees(self.roll),
            'yaw_deg': math.degrees(self.yaw),
            'incline_deg': math.degrees(incline)
        }

# ---------------- SQLite Data Logger ----------------
class SQLiteDataLogger:
    """Handles buffered writing to SQLite database."""
    
    def __init__(self, db_path, buffer_size=50):
        self.db_path = db_path
        self.buffer_size = buffer_size
        self.buffer = deque()
        self.total_logged = 0
        self.total_flushed = 0
        self.imu_processor = IMUProcessor()
        self._setup_database()
    
    def _setup_database(self):
        """Create database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        
        # Enable WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        
        conn.commit()
        conn.close()
        
        print(f"✓ Database ready: {self.db_path}")
    
    def add(self, data):
        """Add data to buffer with IMU processing."""
        timestamp = datetime.now().isoformat()
        
        # Process IMU data if available
        orientation = None
        if all(k in data for k in ['ax', 'ay', 'az', 'gx', 'gy', 'gz']):
            orientation = self.imu_processor.update(
                data['ax'], data['ay'], data['az'],
                data['gx'], data['gy'], data['gz']
            )
        
        entry = (
            timestamp,
            data.get('co2'),
            data.get('voc'),
            data.get('temp'),
            data.get('hum'),
            data.get('ax'),
            data.get('ay'),
            data.get('az'),
            data.get('gx'),
            data.get('gy'),
            data.get('gz'),
            data.get('pos_x'),
            data.get('pos_y'),
            orientation['yaw'] if orientation else data.get('yaw'),
            orientation['pitch'] if orientation else None,
            orientation['roll'] if orientation else None,
            orientation['incline'] if orientation else None
        )
        
        self.buffer.append(entry)
        self.total_logged += 1
        
        return orientation  # Return for display
    
    def flush(self):
        """Write all buffered data to database."""
        if not self.buffer:
            return 0
        
        entries_to_write = list(self.buffer)
        self.buffer.clear()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.executemany("""
                INSERT INTO sensor_data 
                (timestamp, co2, voc, temp, hum, ax, ay, az, gx, gy, gz, 
                 pos_x, pos_y, yaw, pitch, roll, incline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, entries_to_write)
            
            conn.commit()
            conn.close()
            
            self.total_flushed += len(entries_to_write)
            return len(entries_to_write)
        
        except Exception as e:
            print(f"❌ Error writing to database: {e}")
            self.buffer.extend(entries_to_write)
            return 0
    
    def should_flush(self):
        """Check if buffer should be flushed."""
        return len(self.buffer) >= self.buffer_size
    
    def get_stats(self):
        """Return logging statistics."""
        return {
            "total_logged": self.total_logged,
            "total_flushed": self.total_flushed,
            "buffered": len(self.buffer)
        }
    
    def get_db_stats(self):
        """Get database statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM sensor_data")
            row_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT timestamp FROM sensor_data ORDER BY id DESC LIMIT 1")
            latest = cursor.fetchone()
            latest_time = latest[0] if latest else "N/A"
            
            conn.close()
            
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
            
            return {
                "total_rows": row_count,
                "latest_entry": latest_time,
                "db_size_mb": db_size_mb
            }
        except Exception as e:
            return None

# ---------------- Connection Manager ----------------
class ConnectionManager:
    """Manages BLE connection with automatic reconnection."""
    
    def __init__(self, central, reconnect_delay=5.0, max_attempts=0):
        self.central = central
        self.reconnect_delay = reconnect_delay
        self.max_attempts = max_attempts
        self.connected = False
        self.reconnect_count = 0
        self.should_run = True
    
    async def connect_with_retry(self):
        """Try to connect with retries."""
        attempt = 0
        
        while self.should_run:
            if self.max_attempts > 0 and attempt >= self.max_attempts:
                print(f"❌ Max reconnection attempts ({self.max_attempts}) reached")
                return False
            
            attempt += 1
            
            if attempt > 1:
                print(f"🔄 Reconnection attempt {attempt}" + 
                      (f"/{self.max_attempts}" if self.max_attempts > 0 else ""))
            
            try:
                success = await asyncio.wait_for(
                    self.central.connect(),
                    timeout=CONNECTION_TIMEOUT
                )
                
                if success:
                    self.connected = True
                    self.reconnect_count += 1
                    
                    await self.central.send('Start')
                    print("📡 Waiting for databot ready signal...")
                    await asyncio.sleep(2)
                    
                    return True
                else:
                    print(f"⚠️  Connection failed, retrying in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)
                    
            except asyncio.TimeoutError:
                print(f"⏱️  Connection timeout, retrying in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
                
            except Exception as e:
                print(f"❌ Connection error: {e}")
                await asyncio.sleep(self.reconnect_delay)
        
        return False
    
    async def monitor_connection(self):
        """Monitor connection and reconnect if dropped."""
        last_data_time = time.time()
        connection_check_interval = 10.0
        data_timeout = 30.0
        
        while self.should_run:
            await asyncio.sleep(connection_check_interval)
            
            if not self.connected:
                continue
            
            time_since_data = time.time() - last_data_time
            
            if time_since_data > data_timeout:
                print(f"\n⚠️  No data received for {data_timeout}s - connection may be lost")
                self.connected = False
                
                try:
                    if self.central.is_connected:
                        await self.central.disconnect()
                except Exception:
                    pass
                
                print("🔄 Attempting to reconnect...")
                success = await self.connect_with_retry()
                
                if success:
                    print("✓ Reconnected successfully!")
                    last_data_time = time.time()
                else:
                    print("❌ Reconnection failed")
                    break
    
    def update_data_timestamp(self):
        """Call this when data is received."""
        self.last_data_time = time.time()
    
    def stop(self):
        """Stop the connection manager."""
        self.should_run = False

# ---------------- Main Loop ----------------
async def run():
    """Main async loop for BLE connection and data logging."""
    central = BLE_UART_Central()
    logger = SQLiteDataLogger(DB_FILE, BUFFER_SIZE)
    connection_mgr = ConnectionManager(
        central, 
        reconnect_delay=RECONNECT_DELAY,
        max_attempts=MAX_RECONNECT_ATTEMPTS
    )
    
    data_queue = asyncio.Queue()
    last_data_time = time.time()
    latest_orientation = None
    
    def on_receive(data_bytes: bytes):
        nonlocal last_data_time
        last_data_time = time.time()
        
        try:
            text = data_bytes.decode('utf-8')
        except Exception:
            return

        if isinstance(text, str) and text.strip().lower() == 'ready':
            print("✓ Databot is ready")
            return

        try:
            data = json.loads(text)
            asyncio.get_event_loop().call_soon_threadsafe(
                data_queue.put_nowait, 
                data
            )
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"⚠️  Error processing data: {e}")

    central.on_receive(on_receive)

    print("\n" + "="*60)
    print("DATABOT ROVER - DATA LOGGER (IMU Enhanced)")
    print("="*60)
    print("Features:")
    print("  • Auto-reconnect on connection loss")
    print("  • IMU heading and tilt tracking")
    print("  • Incline detection for accurate distance")
    print(f"Database: {DB_FILE}")
    print("="*60 + "\n")
    
    print("🔍 Scanning for databot...")
    success = await connection_mgr.connect_with_retry()
    
    if not success:
        print("❌ Failed to establish initial connection")
        return 1
    
    print("\n" + "="*60)
    print("✓ Connected! Logging data...")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    monitor_task = asyncio.create_task(connection_mgr.monitor_connection())
    
    last_flush = time.time()
    last_stats = time.time()
    
    try:
        while connection_mgr.should_run:
            current_time = time.time()
            
            try:
                data = await asyncio.wait_for(data_queue.get(), timeout=0.1)
                latest_orientation = logger.add(data)
                
            except asyncio.TimeoutError:
                pass
            
            if logger.should_flush() or (current_time - last_flush >= FLUSH_INTERVAL):
                flushed = logger.flush()
                if flushed > 0:
                    last_flush = current_time
            
            if current_time - last_stats >= 10.0:
                stats = logger.get_stats()
                db_stats = logger.get_db_stats()
                
                connection_status = "🟢 Connected" if connection_mgr.connected else "🔴 Disconnected"
                time_since_data = current_time - last_data_time
                
                status_line = f"{connection_status} | Buffer: {stats['buffered']}"
                
                if db_stats:
                    status_line += f" | DB Rows: {db_stats['total_rows']} | Size: {db_stats['db_size_mb']:.2f} MB"
                
                if latest_orientation:
                    status_line += f" | Heading: {latest_orientation['yaw_deg']:.1f}° | Incline: {latest_orientation['incline_deg']:.1f}°"
                
                print(status_line)
                last_stats = current_time
            
            await asyncio.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Shutting down...")
        connection_mgr.stop()
        
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        flushed = logger.flush()
        print(f"✓ Final flush: {flushed} entries written")
        
        stats = logger.get_stats()
        db_stats = logger.get_db_stats()
        
        print(f"\nFinal Statistics:")
        print(f"  Total entries logged: {stats['total_logged']}")
        print(f"  Total entries flushed: {stats['total_flushed']}")
        print(f"  Reconnections: {connection_mgr.reconnect_count - 1}")
        
        if db_stats:
            print(f"\nDatabase Statistics:")
            print(f"  Total rows: {db_stats['total_rows']}")
            print(f"  Size: {db_stats['db_size_mb']:.2f} MB")
        
        print("="*60)
        
        if central.is_connected:
            print("Disconnecting from databot...")
            await central.disconnect()
        
        print("Shutdown complete.")

    return 0

def main():
    """Entry point for the data logger."""
    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        print('\n\nInterrupted by user')
        return 1

if __name__ == "__main__":
    raise SystemExit(main())# main_pi.py
# Raspberry Pi data logger for Databot with auto-reconnect
# Now uses IMU data for heading and tilt calculations

import asyncio
import json
import sqlite3
import time
import os
from datetime import datetime
from collections import deque
from comms.central import BLE_UART_Central
import math

# ---------------- Configuration ----------------
LOG_DIR = "/home/rover_logs"
DB_FILE = os.path.join(LOG_DIR, "rover_data.db")

# Buffer configuration
BUFFER_SIZE = 50           # Write to DB every 50 entries
FLUSH_INTERVAL = 30.0      # Or every 30 seconds

# Reconnection configuration
RECONNECT_DELAY = 5.0      # Seconds to wait before reconnect attempt
MAX_RECONNECT_ATTEMPTS = 0 # 0 = infinite retries
CONNECTION_TIMEOUT = 10.0  # Seconds to wait for connection

# IMU calibration - complementary filter
COMP_FILTER_ALPHA = 0.98   # 98% gyro, 2% accel

# ---------------- Database Schema ----------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    co2 REAL,
    voc REAL,
    temp REAL,
    hum REAL,
    ax REAL,
    ay REAL,
    az REAL,
    gx REAL,
    gy REAL,
    gz REAL,
    pos_x REAL,
    pos_y REAL,
    yaw REAL,
    pitch REAL,
    roll REAL,
    incline REAL
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_position ON sensor_data(pos_x, pos_y);
"""

# ---------------- IMU Data Processor ----------------
class IMUProcessor:
    """Process IMU data for heading, pitch, roll, and incline."""
    
    def __init__(self):
        self.pitch = 0.0      # Pitch angle (radians)
        self.roll = 0.0       # Roll angle (radians)
        self.yaw = 0.0        # Yaw/heading (radians)
        self.last_update = time.time()
    
    def update(self, ax, ay, az, gx, gy, gz):
        """
        Update orientation using complementary filter.
        
        Args:
            ax, ay, az: Accelerometer readings (m/s^2 or g)
            gx, gy, gz: Gyroscope readings (rad/s)
        
        Returns:
            dict with pitch, roll, yaw, incline
        """
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        if dt <= 0 or dt > 1.0:  # Ignore bad time deltas
            dt = 0.02
        
        # --- Pitch from accelerometer (stable but noisy) ---
        try:
            pitch_accel = math.atan2(ax, math.sqrt(ay**2 + az**2))
        except (ValueError, ZeroDivisionError):
            pitch_accel = self.pitch
        
        # --- Roll from accelerometer ---
        try:
            roll_accel = math.atan2(ay, math.sqrt(ax**2 + az**2))
        except (ValueError, ZeroDivisionError):
            roll_accel = self.roll
        
        # --- Integrate gyroscope (fast but drifts) ---
        pitch_gyro = self.pitch + gy * dt
        roll_gyro = self.roll + gx * dt
        yaw_gyro = self.yaw + gz * dt
        
        # --- Complementary filter: fuse accel + gyro ---
        self.pitch = (COMP_FILTER_ALPHA * pitch_gyro) + ((1.0 - COMP_FILTER_ALPHA) * pitch_accel)
        self.roll = (COMP_FILTER_ALPHA * roll_gyro) + ((1.0 - COMP_FILTER_ALPHA) * roll_accel)
        self.yaw = yaw_gyro  # No magnetometer, so yaw drifts (for now)
        
        # Normalize yaw to [-pi, pi]
        while self.yaw > math.pi:
            self.yaw -= 2 * math.pi
        while self.yaw < -math.pi:
            self.yaw += 2 * math.pi
        
        # --- Calculate incline (total tilt from horizontal) ---
        incline = math.sqrt(self.pitch**2 + self.roll**2)
        
        return {
            'pitch': self.pitch,           # radians
            'roll': self.roll,             # radians
            'yaw': self.yaw,               # radians
            'incline': incline,            # radians
            'pitch_deg': math.degrees(self.pitch),
            'roll_deg': math.degrees(self.roll),
            'yaw_deg': math.degrees(self.yaw),
            'incline_deg': math.degrees(incline)
        }

# ---------------- SQLite Data Logger ----------------
class SQLiteDataLogger:
    """Handles buffered writing to SQLite database."""
    
    def __init__(self, db_path, buffer_size=50):
        self.db_path = db_path
        self.buffer_size = buffer_size
        self.buffer = deque()
        self.total_logged = 0
        self.total_flushed = 0
        self.imu_processor = IMUProcessor()
        self._setup_database()
    
    def _setup_database(self):
        """Create database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        
        # Enable WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        
        conn.commit()
        conn.close()
        
        print(f"✓ Database ready: {self.db_path}")
    
    def add(self, data):
        """Add data to buffer with IMU processing."""
        timestamp = datetime.now().isoformat()
        
        # Process IMU data if available
        orientation = None
        if all(k in data for k in ['ax', 'ay', 'az', 'gx', 'gy', 'gz']):
            orientation = self.imu_processor.update(
                data['ax'], data['ay'], data['az'],
                data['gx'], data['gy'], data['gz']
            )
        
        entry = (
            timestamp,
            data.get('co2'),
            data.get('voc'),
            data.get('temp'),
            data.get('hum'),
            data.get('ax'),
            data.get('ay'),
            data.get('az'),
            data.get('gx'),
            data.get('gy'),
            data.get('gz'),
            data.get('pos_x'),
            data.get('pos_y'),
            orientation['yaw'] if orientation else data.get('yaw'),
            orientation['pitch'] if orientation else None,
            orientation['roll'] if orientation else None,
            orientation['incline'] if orientation else None
        )
        
        self.buffer.append(entry)
        self.total_logged += 1
        
        return orientation  # Return for display
    
    def flush(self):
        """Write all buffered data to database."""
        if not self.buffer:
            return 0
        
        entries_to_write = list(self.buffer)
        self.buffer.clear()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.executemany("""
                INSERT INTO sensor_data 
                (timestamp, co2, voc, temp, hum, ax, ay, az, gx, gy, gz, 
                 pos_x, pos_y, yaw, pitch, roll, incline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, entries_to_write)
            
            conn.commit()
            conn.close()
            
            self.total_flushed += len(entries_to_write)
            return len(entries_to_write)
        
        except Exception as e:
            print(f"❌ Error writing to database: {e}")
            self.buffer.extend(entries_to_write)
            return 0
    
    def should_flush(self):
        """Check if buffer should be flushed."""
        return len(self.buffer) >= self.buffer_size
    
    def get_stats(self):
        """Return logging statistics."""
        return {
            "total_logged": self.total_logged,
            "total_flushed": self.total_flushed,
            "buffered": len(self.buffer)
        }
    
    def get_db_stats(self):
        """Get database statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM sensor_data")
            row_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT timestamp FROM sensor_data ORDER BY id DESC LIMIT 1")
            latest = cursor.fetchone()
            latest_time = latest[0] if latest else "N/A"
            
            conn.close()
            
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
            
            return {
                "total_rows": row_count,
                "latest_entry": latest_time,
                "db_size_mb": db_size_mb
            }
        except Exception as e:
            return None

# ---------------- Connection Manager ----------------
class ConnectionManager:
    """Manages BLE connection with automatic reconnection."""
    
    def __init__(self, central, reconnect_delay=5.0, max_attempts=0):
        self.central = central
        self.reconnect_delay = reconnect_delay
        self.max_attempts = max_attempts
        self.connected = False
        self.reconnect_count = 0
        self.should_run = True
    
    async def connect_with_retry(self):
        """Try to connect with retries."""
        attempt = 0
        
        while self.should_run:
            if self.max_attempts > 0 and attempt >= self.max_attempts:
                print(f"❌ Max reconnection attempts ({self.max_attempts}) reached")
                return False
            
            attempt += 1
            
            if attempt > 1:
                print(f"🔄 Reconnection attempt {attempt}" + 
                      (f"/{self.max_attempts}" if self.max_attempts > 0 else ""))
            
            try:
                success = await asyncio.wait_for(
                    self.central.connect(),
                    timeout=CONNECTION_TIMEOUT
                )
                
                if success:
                    self.connected = True
                    self.reconnect_count += 1
                    
                    await self.central.send('Start')
                    print("📡 Waiting for databot ready signal...")
                    await asyncio.sleep(2)
                    
                    return True
                else:
                    print(f"⚠️  Connection failed, retrying in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)
                    
            except asyncio.TimeoutError:
                print(f"⏱️  Connection timeout, retrying in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
                
            except Exception as e:
                print(f"❌ Connection error: {e}")
                await asyncio.sleep(self.reconnect_delay)
        
        return False
    
    async def monitor_connection(self):
        """Monitor connection and reconnect if dropped."""
        last_data_time = time.time()
        connection_check_interval = 10.0
        data_timeout = 30.0
        
        while self.should_run:
            await asyncio.sleep(connection_check_interval)
            
            if not self.connected:
                continue
            
            time_since_data = time.time() - last_data_time
            
            if time_since_data > data_timeout:
                print(f"\n⚠️  No data received for {data_timeout}s - connection may be lost")
                self.connected = False
                
                try:
                    if self.central.is_connected:
                        await self.central.disconnect()
                except Exception:
                    pass
                
                print("🔄 Attempting to reconnect...")
                success = await self.connect_with_retry()
                
                if success:
                    print("✓ Reconnected successfully!")
                    last_data_time = time.time()
                else:
                    print("❌ Reconnection failed")
                    break
    
    def update_data_timestamp(self):
        """Call this when data is received."""
        self.last_data_time = time.time()
    
    def stop(self):
        """Stop the connection manager."""
        self.should_run = False

# ---------------- Main Loop ----------------
async def run():
    """Main async loop for BLE connection and data logging."""
    central = BLE_UART_Central()
    logger = SQLiteDataLogger(DB_FILE, BUFFER_SIZE)
    connection_mgr = ConnectionManager(
        central, 
        reconnect_delay=RECONNECT_DELAY,
        max_attempts=MAX_RECONNECT_ATTEMPTS
    )
    
    data_queue = asyncio.Queue()
    last_data_time = time.time()
    latest_orientation = None
    
    def on_receive(data_bytes: bytes):
        nonlocal last_data_time
        last_data_time = time.time()
        
        try:
            text = data_bytes.decode('utf-8')
        except Exception:
            return

        if isinstance(text, str) and text.strip().lower() == 'ready':
            print("✓ Databot is ready")
            return

        try:
            data = json.loads(text)
            asyncio.get_event_loop().call_soon_threadsafe(
                data_queue.put_nowait, 
                data
            )
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"⚠️  Error processing data: {e}")

    central.on_receive(on_receive)

    print("\n" + "="*60)
    print("DATABOT ROVER - DATA LOGGER (IMU Enhanced)")
    print("="*60)
    print("Features:")
    print("  • Auto-reconnect on connection loss")
    print("  • IMU heading and tilt tracking")
    print("  • Incline detection for accurate distance")
    print(f"Database: {DB_FILE}")
    print("="*60 + "\n")
    
    print("🔍 Scanning for databot...")
    success = await connection_mgr.connect_with_retry()
    
    if not success:
        print("❌ Failed to establish initial connection")
        return 1
    
    print("\n" + "="*60)
    print("✓ Connected! Logging data...")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    monitor_task = asyncio.create_task(connection_mgr.monitor_connection())
    
    last_flush = time.time()
    last_stats = time.time()
    
    try:
        while connection_mgr.should_run:
            current_time = time.time()
            
            try:
                data = await asyncio.wait_for(data_queue.get(), timeout=0.1)
                latest_orientation = logger.add(data)
                
            except asyncio.TimeoutError:
                pass
            
            if logger.should_flush() or (current_time - last_flush >= FLUSH_INTERVAL):
                flushed = logger.flush()
                if flushed > 0:
                    last_flush = current_time
            
            if current_time - last_stats >= 10.0:
                stats = logger.get_stats()
                db_stats = logger.get_db_stats()
                
                connection_status = "🟢 Connected" if connection_mgr.connected else "🔴 Disconnected"
                time_since_data = current_time - last_data_time
                
                status_line = f"{connection_status} | Buffer: {stats['buffered']}"
                
                if db_stats:
                    status_line += f" | DB Rows: {db_stats['total_rows']} | Size: {db_stats['db_size_mb']:.2f} MB"
                
                if latest_orientation:
                    status_line += f" | Heading: {latest_orientation['yaw_deg']:.1f}° | Incline: {latest_orientation['incline_deg']:.1f}°"
                
                print(status_line)
                last_stats = current_time
            
            await asyncio.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Shutting down...")
        connection_mgr.stop()
        
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        flushed = logger.flush()
        print(f"✓ Final flush: {flushed} entries written")
        
        stats = logger.get_stats()
        db_stats = logger.get_db_stats()
        
        print(f"\nFinal Statistics:")
        print(f"  Total entries logged: {stats['total_logged']}")
        print(f"  Total entries flushed: {stats['total_flushed']}")
        print(f"  Reconnections: {connection_mgr.reconnect_count - 1}")
        
        if db_stats:
            print(f"\nDatabase Statistics:")
            print(f"  Total rows: {db_stats['total_rows']}")
            print(f"  Size: {db_stats['db_size_mb']:.2f} MB")
        
        print("="*60)
        
        if central.is_connected:
            print("Disconnecting from databot...")
            await central.disconnect()
        
        print("Shutdown complete.")

    return 0

def main():
    """Entry point for the data logger."""
    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        print('\n\nInterrupted by user')
        return 1

if __name__ == "__main__":
    raise SystemExit(main())