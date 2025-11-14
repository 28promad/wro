# main_databot_test.py
# Laptop-side test for receiving data from Databot and logging to CSV

import json
import csv
import os
import time
import serial  # pyserial required

# ---------------- Configuration ----------------
LOG_DIR = "./rover_logs"
CSV_FILE = os.path.join(LOG_DIR, "data_log.csv")
SERIAL_PORT = "/dev/ttyUSB0"  # update if different on your laptop
BAUDRATE = 115200

# ---------------- Serial Setup ----------------
def initialise_serial():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.1)
        print(f"Connected to Databot on {SERIAL_PORT}")
        return ser
    except Exception as e:
        print("Serial connection error:", e)
        return None

def send_to_databot(ser, msg):
    if ser:
        ser.write(msg.encode() + b"\n")

def read_from_databot(ser):
    if ser and ser.in_waiting:
        line = ser.readline().decode("utf-8").strip()
        return line
    return None

# ---------------- CSV Logging ----------------
def log_data(data):
    os.makedirs(LOG_DIR, exist_ok=True)
    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(data)

# ---------------- Main Loop ----------------
def main():
    ser = initialise_serial()
    if not ser:
        return

    print("Sending Start command to Databot...")
    send_to_databot(ser, "Start")

    try:
        while True:
            msg = read_from_databot(ser)
            if not msg:
                time.sleep(0.05)
                continue

            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                print("Received (not JSON):", msg)
                continue

            log_data(data)
            print("Logged data:", data)

    except KeyboardInterrupt:
        print("\nStopped manually.")
    finally:
        if ser:
            ser.close()
        print("Serial connection closed.")

# ---------------- Entry Point ----------------
if __name__ == "__main__":
    main()
