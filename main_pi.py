# main_pi.py
# Raspberry Pi main controller for Databot-based rover

from comms import serial_pi
from motor_control import MotorController
import RPi.GPIO as GPIO
import json, csv, time, os

# ---------------- Configuration ----------------
LOG_DIR = "/home/pi/rover_logs"
CSV_FILE = os.path.join(LOG_DIR, "data_log.csv")
TUNNEL_LENGTH = 10.0   # metres (set to your mine tunnel length)
OBSTACLE_DIST = 15.0   # cm threshold for obstacle detection

# Ultrasonic sensors: (trigger_pin, echo_pin)
ULTRASONIC_PINS = {
    "left":  (5, 6),
    "front": (13, 19),
    "right": (26, 21)
}

# ---------------- Setup Functions ----------------
def setup_ultrasonic():
    GPIO.setmode(GPIO.BCM)
    for trig, echo in ULTRASONIC_PINS.values():
        GPIO.setup(trig, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)
        GPIO.output(trig, False)

def distance(trig, echo):
    """Return distance in cm from one ultrasonic pair."""
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    start, end = time.time(), time.time()
    timeout = start + 0.04  # 40 ms timeout
    while GPIO.input(echo) == 0 and time.time() < timeout:
        start = time.time()
    while GPIO.input(echo) == 1 and time.time() < timeout:
        end = time.time()
    duration = end - start
    return (duration * 34300) / 2

def get_obstacles():
    """Read all three ultrasonic sensors."""
    readings = {}
    for pos, pins in ULTRASONIC_PINS.items():
        try:
            readings[pos] = distance(*pins)
            time.sleep(0.01)  # Small delay between readings
        except Exception as e:
            print(f"Error reading {pos} sensor: {e}")
            readings[pos] = float('inf')
    return readings

def handle_obstacle_avoidance(motor, readings):
    """Handle obstacle avoidance based on ultrasonic sensor readings."""
    left_dist = readings.get('left', float('inf'))
    front_dist = readings.get('front', float('inf'))
    right_dist = readings.get('right', float('inf'))
    
    # If obstacle detected in front
    if front_dist < OBSTACLE_DIST:
        motor.stop()
        time.sleep(0.1)
        
        # Decide which way to turn based on side sensors
        if left_dist > right_dist:
            print(f"Obstacle front, turning left (L:{left_dist:.1f}, R:{right_dist:.1f})")
            motor.turn_left(0.4)  # Adjust turn duration as needed
        else:
            print(f"Obstacle front, turning right (L:{left_dist:.1f}, R:{right_dist:.1f})")
            motor.turn_right(0.4)  # Adjust turn duration as needed
        
        return True
    
    # Handle diagonal sensors for course correction
    elif left_dist < OBSTACLE_DIST:
        print(f"Obstacle on left ({left_dist:.1f}cm), adjusting right")
        motor.set_speed(60)  # Reduce speed for gentle correction
        motor.turn_right(0.2)
        motor.set_speed(75)  # Reset to normal speed
        return True
    
    elif right_dist < OBSTACLE_DIST:
        print(f"Obstacle on right ({right_dist:.1f}cm), adjusting left")
        motor.set_speed(60)  # Reduce speed for gentle correction
        motor.turn_left(0.2)
        motor.set_speed(75)  # Reset to normal speed
        return True
    
    return False
        except Exception:
            readings[pos] = 999
    return readings

def log_data(data):
    """Append one line of sensor data to CSV file."""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(data.keys()))
        if f.tell() == 0:  # If file is empty, write header
            writer.writeheader()
        writer.writerow(data)

def main():
    """Main control loop for the rover."""
    motor = None
    try:
        # Initialize components
        setup_ultrasonic()
        motor = MotorController()
        serial_pi.initialise('/dev/ttyUSB0')
        print("Rover initialized successfully")
        
        while True:
            # Get sensor readings
            obstacle_readings = get_obstacles()
            
            # Check for obstacles and handle avoidance
            if handle_obstacle_avoidance(motor, obstacle_readings):
                continue  # Skip to next iteration if we had to avoid an obstacle
            
            # If no obstacles, continue forward
            motor.forward()
            
            # Get sensor data from Databot
            msg = serial_pi.read_from_databot()
            if msg:
                try:
                    data = json.loads(msg)
                    log_data(data)
                except json.JSONDecodeError as e:
                    print(f"Error decoding data: {e}")
            
            time.sleep(0.05)  # Small delay to prevent CPU overload
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if motor:
            motor.stop()
        GPIO.cleanup()
        
if __name__ == "__main__":
    main()
    write_header = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(data)

# ---------------- Navigation Logic ----------------
def main():
    print("Initializing serial link...")
    serial_pi.initialise('/dev/ttyUSB0')
    setup_ultrasonic()
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
            print("Parse error:", msg)
            continue

        log_data(data)  # save everything
        disp = float(data.get("disp", 0))
        obstacles = get_obstacles()
        left, front, right = obstacles["left"], obstacles["front"], obstacles["right"]

        print(f"disp={disp:.2f} m | front={front:.1f} cm | L={left:.1f} cm | R={right:.1f} cm")

        # --- Obstacle avoidance ---
        if all(d < OBSTACLE_DIST for d in obstacles.values()):
            print("All sides blocked → turning around")
            motor.turn_around()
            reverse = not reverse

        elif front < OBSTACLE_DIST:
            if left > right:
                print("Obstacle ahead → turning left")
                motor.turn_left()
            else:
                print("Obstacle ahead → turning right")
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
