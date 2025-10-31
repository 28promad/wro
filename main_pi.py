# main_pi.py
# Raspberry Pi main controller for Databot-based rover (using IR sensors)

from comms import serial_pi
from motor_control import MotorController
import RPi.GPIO as GPIO
import json, csv, time, os, tempfile, shutil

# ---------------- Configuration ----------------
LOG_DIR = "/home/pi/rover_logs"
CSV_FILE = os.path.join(LOG_DIR, "data_log.csv")
SHARED_FILE = "/home/pi/rover/shared_data.json"

TUNNEL_LENGTH = 10.0   # metres
OBSTACLE_DETECTED = 0  # IR sensors output LOW when blocked

# IR sensor GPIO pins
IR_PINS = {
    "left": 5,
    "front": 6,
    "right": 13
}

# ---------------- Setup Functions ----------------
def setup_ir():
    GPIO.setmode(GPIO.BCM)
    for pin in IR_PINS.values():
        GPIO.setup(pin, GPIO.IN)

def read_ir():
    """Return dict with True if obstacle detected."""
    states = {}
    for pos, pin in IR_PINS.items():
        val = GPIO.input(pin)
        states[pos] = (val == OBSTACLE_DETECTED)
    return states

def log_data(data):
    """Append one line of sensor data to CSV file."""
    os.makedirs(LOG_DIR, exist_ok=True)
    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(data)

def update_shared_data(data):
    """Safely write latest readings to a JSON file for the web app."""
    try:
        os.makedirs(os.path.dirname(SHARED_FILE), exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(SHARED_FILE)) as tmp:
            json.dump(data, tmp)
            tempname = tmp.name
        shutil.move(tempname, SHARED_FILE)
    except Exception as e:
        print("Shared data write error:", e)

# ---------------- Navigation Logic ----------------
def main():
    print("Initializing serial link...")
    serial_pi.initialise('/dev/ttyUSB0')
    setup_ir()
    motor = MotorController()
    serial_pi.send_to_databot("Start")

    print("Waiting for Databot...")
    reverse = False

    while True:
        msg = serial_pi.read_from_databot()
        if not msg:
            time.sleep(0.05)
            continue

        try:
            data = json.loads(msg)
        except Exception:
            continue

        # Log and share
        log_data(data)
        update_shared_data(data)

        disp = float(data.get("disp", 0))
        ir = read_ir()
        left, front, right = ir["left"], ir["front"], ir["right"]

        print(f"disp={disp:.2f} m | IR -> L:{left} F:{front} R:{right}")

        # --- Obstacle avoidance ---
        if left and front and right:
            print("All sides blocked → turning around")
            motor.turn_around()
            reverse = not reverse

        elif front:
            if not left and right:
                print("Obstacle ahead → turning left")
                motor.turn_left()
            elif not right and left:
                print("Obstacle ahead → turning right")
                motor.turn_right()
            else:
                print("Front blocked → turning right by default")
                motor.turn_right()
        else:
            motor.forward()

        # --- Tunnel-end and return logic ---
        if not reverse and disp >= TUNNEL_LENGTH:
            print("Reached tunnel end → turning around")
            motor.turn_around()
            reverse = True
        elif reverse and abs(disp) <= 0.2:
            print("Returned to origin → stopping rover")
            motor.stop()
            break

        time.sleep(0.1)

# ---------------- Entry Point ----------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("\nStopped manually.")
    except Exception as e:
        GPIO.cleanup()
        print("Error:", e)
