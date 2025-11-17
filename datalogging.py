# main_pi.py
# Raspberry Pi data logger for Databot-based rover (BLE version)
# Uses SQLite for efficient storage and easy querying

import asyncio
import json
import sqlite3
import time
import os
from datetime import datetime
from collections import deque
from comms.central import BLE_UART_Central

# ---------------- Configuration ----------------
LOG_DIR = "./"
DB_FILE = os.path.join(LOG_DIR, "rover_data.db")

# Buffer configuration
BUFFER_SIZE = 50           # Write to DB every 50 entries
FLUSH_INTERVAL = 5.0      # Or every 5 seconds, whichever comes first

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
    yaw REAL
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_position ON sensor_data(pos_x, pos_y);
"""

# ---------------- SQLite Data Logger ----------------
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
        conn.executescript(SCHEMA)
        
        # Enable WAL mode for better concurrent access (important for Flask!)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")  # Faster, still safe
        
        conn.commit()
        conn.close()
        
        print(f"✓ Database ready: {self.db_path}")
    
    def add(self, data):
        """Add data to buffer (non-blocking)."""
        # Add timestamp
        timestamp = datetime.now().isoformat()
        
        # Extract fields in order
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
            data.get('yaw')
        )
        
        self.buffer.append(entry)
        self.total_logged += 1
    
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
                (timestamp, co2, voc, temp, hum, ax, ay, az, gx, gy, gz, pos_x, pos_y, yaw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, entries_to_write)
            
            conn.commit()
            conn.close()
            
            self.total_flushed += len(entries_to_write)
            return len(entries_to_write)
        
        except Exception as e:
            print(f"❌ Error writing to database: {e}")
            # Put data back in buffer to retry
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
        """Get database statistics (total rows, size, etc.)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get row count
            cursor.execute("SELECT COUNT(*) FROM sensor_data")
            row_count = cursor.fetchone()[0]
            
            # Get latest entry
            cursor.execute("SELECT timestamp FROM sensor_data ORDER BY id DESC LIMIT 1")
            latest = cursor.fetchone()
            latest_time = latest[0] if latest else "N/A"
            
            conn.close()
            
            # Get file size
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
            
            return {
                "total_rows": row_count,
                "latest_entry": latest_time,
                "db_size_mb": db_size_mb
            }
        except Exception as e:
            print(f"❌ Error getting DB stats: {e}")
            return None

# ---------------- Main Loop ----------------
async def run():
    """Main async loop for BLE connection and data logging."""
    central = BLE_UART_Central()
    ready_event = asyncio.Event()
    
    # Initialize SQLite logger
    logger = SQLiteDataLogger(DB_FILE, BUFFER_SIZE)
    
    last_flush_time = time.time()
    last_stats_time = time.time()

    def on_receive(data_bytes: bytes):
        # Try to decode
        try:
            text = data_bytes.decode('utf-8')
        except Exception:
            text = repr(data_bytes)
            print(f"⚠ Could not decode data: {text}")
            return

        # Check for 'ready' message
        if isinstance(text, str) and text.strip().lower() == 'ready':
            ready_event.set()
            print("✓ Databot is ready")
            return

        # Try to parse as JSON and add to buffer
        try:
            data = json.loads(text)
            logger.add(data)  # Non-blocking add to buffer
        
        except json.JSONDecodeError:
            print(f"⚠ Received non-JSON data: {text[:50]}...")
        except Exception as e:
            print(f"❌ Error processing data: {e}")

    central.on_receive(on_receive)

    # Connect to databot
    print("\n" + "="*60)
    print("DATABOT ROVER - DATA LOGGER (SQLite)")
    print("="*60)
    print("Starting BLE scan and connection...")
    
    if not await central.connect():
        print("❌ Failed to connect to databot.")
        return 1

    try:
        # Send Start command
        print("📡 Sending 'Start' command to databot...")
        await central.send('Start')

        # Wait for ready confirmation
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            print("⚠ Timed out waiting for 'ready' (continuing to listen)")

        print("\n" + "="*60)
        print(f"✓ Connected! Logging to: {DB_FILE}")
        print(f"Buffer size: {BUFFER_SIZE} entries | Flush interval: {FLUSH_INTERVAL}s")
        print("Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        # Main loop: periodic flushing and stats
        while True:
            await asyncio.sleep(1)
            
            current_time = time.time()
            
            # Flush if buffer is full OR time interval has passed
            if logger.should_flush() or (current_time - last_flush_time >= FLUSH_INTERVAL):
                flushed = logger.flush()
                if flushed > 0:
                    last_flush_time = current_time
            
            # Print stats every 10 seconds
            if current_time - last_stats_time >= 10.0:
                stats = logger.get_stats()
                db_stats = logger.get_db_stats()
                
                if db_stats:
                    print(f"📊 Buffer: {stats['buffered']} | "
                          f"DB Rows: {db_stats['total_rows']} | "
                          f"Size: {db_stats['db_size_mb']:.2f} MB")
                else:
                    print(f"📊 Logged: {stats['total_logged']} | "
                          f"Flushed: {stats['total_flushed']} | "
                          f"Buffered: {stats['buffered']}")
                
                last_stats_time = current_time

    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Shutting down...")
        
        # Final flush
        flushed = logger.flush()
        print(f"✓ Final flush: {flushed} entries written")
        
        stats = logger.get_stats()
        db_stats = logger.get_db_stats()
        
        print(f"\nFinal Statistics:")
        print(f"  Total entries logged: {stats['total_logged']}")
        print(f"  Total entries flushed: {stats['total_flushed']}")
        print(f"  Entries lost: {stats['total_logged'] - stats['total_flushed']}")
        
        if db_stats:
            print(f"\nDatabase Statistics:")
            print(f"  Total rows in DB: {db_stats['total_rows']}")
            print(f"  Database size: {db_stats['db_size_mb']:.2f} MB")
            print(f"  Latest entry: {db_stats['latest_entry']}")
        
        print("="*60)
    
    finally:
        if central.is_connected:
            print("Disconnecting from databot...")
            await central.disconnect()
        print("Shutdown complete.")

    return 0

# ---------------- Entry Point ----------------
def main():
    """Entry point for the data logger."""
    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        print('\n\nInterrupted by user')
        return 1

if __name__ == "__main__":
    raise SystemExit(main())