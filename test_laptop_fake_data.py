# main_databot_sim.py
# Simulated Databot data for testing CSV logging on a laptop

import json
import csv
import os
import time
import random

LOG_DIR = "./rover_logs"
CSV_FILE = os.path.join(LOG_DIR, "data_log.csv")

def log_data(data):
    os.makedirs(LOG_DIR, exist_ok=True)
    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(data)

def generate_fake_data():
    return {
        "temp": round(random.uniform(20, 30), 1),
        "hum": round(random.uniform(30, 60), 1),
        "co2": round(random.uniform(350, 600), 1),
        "tvoc": round(random.uniform(100, 1000), 0)  # TVOC typically in ppb (parts per billion)
    }

def main():
    print("Simulating Databot data logging...")
    try:
        while True:
            data = generate_fake_data()
            log_data(data)
            print("Logged data:", data)
            time.sleep(1)  # simulate a message every 1s
    except KeyboardInterrupt:
        print("\nSimulation stopped.")

if __name__ == "__main__":
    main()
