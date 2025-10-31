# main_pi.py
from comms import serial_pi
from motor_control import MotorController
import RPi.GPIO as GPIO
import json, csv, time, math, os

# --- Setup paths ---
LOG_DIR = "/home/pi/rover_logs"
CSV_FILE = os.path.join(LOG_DIR, "data_log.csv")
TUNNEL_LENGTH = 10.0  # metres

# --- Sensor pins ---
ULTRASONIC_PINS = {
    "left": (5, 6),
    "front": (13, 19),
    "right": (26, 21)
}

def setup_ultrasonic():
    GPIO.setmode(GPIO.BCM)
    for trig, echo in ULTRASONIC_PINS.values():
        GPIO.setup(trig, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)
        GPIO.output(trig, False)

def distance(trig, echo):
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)
    start, end = time.time(), time.time()
    while GPIO.input(echo) == 0:
        start = time.time()
    while GPIO.input(echo) == 1:
        end = time.time()
    return ((end - start) * 34300) / 2  # cm

def any_obstacle():
    readings = {pos: distance(*pins) for pos, pins in ULTRASONIC_PINS.items()}
    return readings

def log_data(data):
    os.makedirs(LOG_DIR, exist_ok=True)
    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(data)

def displacement_from_accel(ax, ay, az, dt):
    # Simplified 1D displacement using x-axis (assuming aligned tunnel)
    velocity = getattr(displacement_from_accel, "v", 0)
    displacement = getattr(displacement_from_accel, "d", 0)
    velocity += ax * dt
    displacement += velocity * dt
    displacement_from_accel.v = velocity
    displacement_from_accel.d = displacement
    return displacement

def main():
    serial_pi.initialise('/dev/ttyUSB0')
    setup_ultrasonic()
    motor = MotorController()
    serial_pi.send_to_databot("Start")

    print("Waiting for Databot data...")
    last_update = time.time()
    reverse = False

    while True:
        msg = serial_pi.read_from_databot()
        if msg:
            try:
                data = json.loads(msg)
                log_data(data)

                ax = float(data.get("ax", 0))
                dt = time.time() - last_update
                disp = displacement_from_accel(ax, 0, 0, dt)
                last_update = time.time()

                obstacles = any_obstacle()
                front, left, right = obstacles["front"], obstacles["left"], obstacles["right"]
                print(f"Displacement={disp:.2f}m | Obstacles={obstacles}")

                # Navigation logic
                if all(x < 15 for x in obstacles.values()):
                    motor.turn_around()
                    reverse = not reverse
                elif front < 15:
                    if left > right:
                        motor.turn_left()
                    else:
                        motor.turn_right()
                else:
                    motor.forward()

                # End-of-tunnel detection
                if not reverse and disp >= TUNNEL_LENGTH:
                    motor.turn_around()
                    reverse = True
                elif reverse and abs(disp) <= 0.2:
                    motor.stop()
                    print("Returned to origin — mission complete.")
                    break
            except Exception as e:
                print("Parse error:", e)

        time.sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("\nStopped.")
