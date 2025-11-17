# main_pi.py
# Raspberry Pi data logger for Databot-based rover (BLE version)
# Uses buffered logging with periodic flushes to reduce I/O operations

import asyncio
import json
import csv
import time
import os
from datetime import datetime
from collections import deque
from comms.central import BLE_UART_Central

# ---------------- Configuration ----------------
LOG_DIR = "/home/rover_logs"
CSV_FILE = os.path.join(LOG_DIR, "data_log.csv")

# Buffer configuration
BUFFER_SIZE = 50           # Write to disk every 50 entries
FLUSH_INTERVAL = 30.0      # Or every 30 seconds, whichever comes first

# CSV fieldnames - matches the data structure from databot
CSV_FIELDNAMES = [
    "timestamp",
    "co2", "voc", "temp", "hum",
    "ax", "ay", "az",
    "gx", "gy", "gz",
    "pos_x", "pos_y", "yaw"
]

# ---------------- Buffered Data Logger ----------------
class BufferedDataLogger:
    """Handles buffered writing to CSV to reduce disk I/O."""
    
    def __init__(self, filepath, fieldnames, buffer_size=50):
        self.filepath = filepath
        self.fieldnames = fieldnames
        self.buffer_size = buffer_size
        self.buffer = deque()
        self.total_logged = 0
        self.total_flushed = 0
        self._setup_file()
    
    def _setup_file(self):
        """Create log directory and initialize CSV file with headers if needed."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        
        file_exists = os.path.exists(self.filepath) and os.path.getsize(self.filepath) > 0
        
        if not file_exists:
            with open(self.filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
            print(f"✓ Created new log file: {self.filepath}")
        else:
            print(f"✓ Using existing log file: {self.filepath}")
    
    def add(self, data):
        """Add data to buffer (non-blocking)."""
        # Add timestamp
        data["timestamp"] = datetime.now().isoformat()
        
        # Ensure all expected fields exist
        log_entry = {field: data.get(field, None) for field in self.fieldnames}
        
        self.buffer.append(log_entry)
        self.total_logged += 1
    
    def flush(self):
        """Write all buffered data to disk."""
        if not self.buffer:
            return 0
        
        entries_to_write = list(self.buffer)
        self.buffer.clear()
        
        try:
            with open(self.filepath, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writerows(entries_to_write)
            
            self.total_flushed += len(entries_to_write)
            return len(entries_to_write)
        
        except Exception as e:
            print(f"❌ Error writing to CSV: {e}")
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

# ---------------- Main Loop ----------------
async def run():
    """Main async loop for BLE connection and data logging."""
    central = BLE_UART_Central()
    ready_event = asyncio.Event()
    
    # Initialize buffered logger
    logger = BufferedDataLogger(CSV_FILE, CSV_FIELDNAMES, BUFFER_SIZE)
    
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
    print("DATABOT ROVER - DATA LOGGER")
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
        print(f"✓ Connected! Logging to: {CSV_FILE}")
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
        print(f"\nFinal Statistics:")
        print(f"  Total entries logged: {stats['total_logged']}")
        print(f"  Total entries flushed: {stats['total_flushed']}")
        print(f"  Entries lost: {stats['total_logged'] - stats['total_flushed']}")
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