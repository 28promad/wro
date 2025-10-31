import RPi.GPIO as GPIO
from comms import serial_pi
from time import sleep, time
import json
from movement.motor_controller import MotorController

# Motor configuration
RIGHT_MOTOR = (17, 27, 4)  # IN1, IN2, EN_A
LEFT_MOTOR = (5, 6, 13)    # IN3, IN4, EN_B

# Ultrasonic sensor pins
FRONT_TRIG = 23
FRONT_ECHO = 24
LEFT_TRIG = 25
LEFT_ECHO = 8
RIGHT_TRIG = 7
RIGHT_ECHO = 12

# Distance thresholds (in cm)
FRONT_THRESHOLD = 30
DIAGONAL_THRESHOLD = 40

def setup_ultrasonic():
    # Setup ultrasonic sensor pins
    for trig in [FRONT_TRIG, LEFT_TRIG, RIGHT_TRIG]:
        GPIO.setup(trig, GPIO.OUT)
    for echo in [FRONT_ECHO, LEFT_ECHO, RIGHT_ECHO]:
        GPIO.setup(echo, GPIO.IN)

def get_distance(trig_pin, echo_pin):
    """Get distance reading from ultrasonic sensor"""
    GPIO.output(trig_pin, GPIO.LOW)
    sleep(0.000002)
    GPIO.output(trig_pin, GPIO.HIGH)
    sleep(0.00001)
    GPIO.output(trig_pin, GPIO.LOW)

    # Wait for echo to start (timeout after 1 second)
    timeout_start = time()
    pulse_start = time()
    while GPIO.input(echo_pin) == 0:
        pulse_start = time()
        if time() - timeout_start > 1:
            return float('inf')

    # Wait for echo to end (timeout after 1 second)
    timeout_start = time()
    pulse_end = time()
    while GPIO.input(echo_pin) == 1:
        pulse_end = time()
        if time() - timeout_start > 1:
            return float('inf')

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150  # Speed of sound * time / 2
    return round(distance, 2)



def parse_sensor_data(data):
    """Parse sensor data from databot"""
    try:
        if data.startswith('data:'):
            temp, humidity, co2, tvoc = map(float, data[5:].split(','))
            return {'temperature': temp, 'humidity': humidity, 'co2': co2, 'tvoc': tvoc}
    except Exception as e:
        print(f"Error parsing sensor data: {e}")
    return None

def check_environment(sensor_data):
    """Check environmental conditions and control LEDs/buzzer"""
    if sensor_data:
        # Example thresholds - adjust as needed
        if sensor_data['co2'] > 1000:  # High CO2
            serial_pi.send_to_databot('led0:(255,0,0,100)')  # Red warning
            serial_pi.send_to_databot('buzzer:(2000,50)')  # Warning beep
        elif sensor_data['tvoc'] > 500:  # High VOC
            serial_pi.send_to_databot('led1:(255,165,0,100)')  # Orange warning
        else:
            serial_pi.send_to_databot('led2:(0,255,0,100)')  # Green - all good

def main():
    try:
        # Initialize motor controller and sensors
        motors = MotorController(right_motor_pins=RIGHT_MOTOR, left_motor_pins=LEFT_MOTOR)
        setup_ultrasonic()
        
        # Setup serial connection and handshake
        max_retries = 3
        retry_count = 0
        handshake_complete = False
        while retry_count < max_retries and not handshake_complete:
            if serial_pi.initialise('/dev/ttyUSB0'):
                serial_pi.send_to_databot("Start")
                # Wait for ready response
                for _ in range(5):
                    response = serial_pi.read_from_databot()
                    if response == "ready":
                        serial_pi.send_to_databot("ack")
                        handshake_complete = True
                        print("[OK] Databot ready")
                        break
                    sleep(1)
                if not handshake_complete:
                    print("[Error] No ready response from Databot")
                    retry_count += 1
                    continue
                break
            retry_count += 1
            sleep(2)
        if not handshake_complete:
            raise RuntimeError("Failed to establish connection with Databot")

        while True:
            # Get distances from ultrasonic sensors
            front_dist = get_distance(FRONT_TRIG, FRONT_ECHO)
            left_dist = get_distance(LEFT_TRIG, LEFT_ECHO)
            right_dist = get_distance(RIGHT_TRIG, RIGHT_ECHO)

            # Get databot sensor readings in simplified format
            raw_data = serial_pi.read_from_databot()
            if raw_data is None or not raw_data.startswith('S|'):
                continue  # No valid data received, skip this loop
            try:
                temp, humidity, co2, tvoc = map(float, raw_data[2:].split(','))
                sensor_data = {'temperature': temp, 'humidity': humidity, 'co2': co2, 'tvoc': tvoc}
            except Exception as e:
                print(f"Error parsing sensor data: {e}")
                continue

            # Example environment logic using new command format
            if sensor_data['co2'] > 1000:
                serial_pi.send_to_databot('L|0,255,0,0,100')  # Red warning
                serial_pi.send_to_databot('B|2000,50')        # Warning beep
            elif sensor_data['tvoc'] > 500:
                serial_pi.send_to_databot('L|1,255,165,0,100')  # Orange warning
            else:
                serial_pi.send_to_databot('L|2,0,255,0,100')    # Green - all good

            # Navigation logic
            if front_dist < FRONT_THRESHOLD:
                motors.stop()
                # Choose direction based on diagonal sensors
                if left_dist > right_dist and left_dist > DIAGONAL_THRESHOLD:
                    motors.turn_left()
                    sleep(0.5)
                elif right_dist > DIAGONAL_THRESHOLD:
                    motors.turn_right()
                    sleep(0.5)
                else:
                    motors.turn_right()
                    sleep(1)
            else:
                motors.forward()

            sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
        motors.cleanup()
    except Exception as e:
        print(f"Error in main loop: {e}")
        motors.cleanup()

if __name__ == "__main__":
    main()


