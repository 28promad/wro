 # main_pi.py
# Raspberry Pi main controller for Databot-based rover (BLE version)

from motor_control import MotorController
from rover_data_service import get_service
import RPi.GPIO as GPIO
import json, csv, time, os, asyncio
from comms.central import BLE_UART_Central, connection_manager

# ---------------- Configuration ----------------
# Use /home/phil/rover_logs on production Pi, fall back to local directory
LOG_DIR = "/home/phil/rover_logs" if os.path.exists("/home/phil") else "./rover_logs"
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

    

def log_data(data):
    """
    Update shared data service for real-time dashboard.
    Also append to CSV file for historical logging.
    """
    service = get_service()
    
    # Update the real-time service (fast, in-memory)
    service.update(data)
    
    # Also log to CSV periodically (optional, for AI training data)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(data.keys()))
        if f.tell() == 0:  # If file is empty, write header
            writer.writeheader()
        writer.writerow(data)

def main():
    """Main control loop for the rover."""
    motor = None
    service = get_service()

    async def async_main():
        nonlocal motor
        central = BLE_UART_Central()
        data_queue = asyncio.Queue()

        def handle_databot_rx(raw):
            try:
                text = raw.decode('utf-8')
            except Exception:
                text = repr(raw)
            # Push JSON messages to queue for processing
            try:
                data = json.loads(text)
            except Exception:
                return
            asyncio.get_event_loop().call_soon_threadsafe(data_queue.put_nowait, data)

        central.on_receive(handle_databot_rx)

        print("Rover initializing (BLE)...")
        setup_ultrasonic()
        motor = MotorController()

        # Start background connection manager (auto-reconnect loop)
        asyncio.create_task(connection_manager(central))

        # Attempt to send start command once connected
        async def ensure_connected_and_start():
            while not central.is_connected:
                await asyncio.sleep(0.5)
            await central.send("Start")
            service.set_connected(True)
            print("Connected to Databot!")

        asyncio.create_task(ensure_connected_and_start())

        try:
            last_connection_check = time.time()
            
            while True:
                # Check connection status every 2 seconds
                now = time.time()
                if now - last_connection_check > 2.0:
                    if central.is_connected:
                        service.set_connected(True)
                    else:
                        service.set_connected(False)
                    last_connection_check = now

                # Read sensors in threads to avoid blocking event loop
                left = await asyncio.to_thread(distance, *ULTRASONIC_PINS['left'])
                front = await asyncio.to_thread(distance, *ULTRASONIC_PINS['front'])
                right = await asyncio.to_thread(distance, *ULTRASONIC_PINS['right'])
                readings = {"left": left, "front": front, "right": right}

                # Obstacle handling (synchronous motor calls are fine)
                if handle_obstacle_avoidance(motor, readings):
                    await asyncio.sleep(0.05)
                    continue

                motor.forward()

                # Process incoming databot messages if any
                try:
                    data = data_queue.get_nowait()
                except asyncio.QueueEmpty:
                    data = None

                if data:
                    log_data(data)
                else:
                    # Even if not connected, update the service to show rover is running
                    # This keeps the dashboard responsive
                    service.set_connected(central.is_connected)

                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            print("Shutting down async main")
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            service.set_connected(False)
            if motor:
                motor.stop()
            GPIO.cleanup()

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        service.set_connected(False)
        GPIO.cleanup()
        print("\nStopped manually.")

if __name__ == "__main__":
    main()
