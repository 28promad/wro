# motor_control.py

import RPi.GPIO as GPIO
import time

# --- Pin configuration ---

MOTOR_LEFT_FORWARD = 17
MOTOR_LEFT_BACKWARD = 27
MOTOR_RIGHT_FORWARD = 23
MOTOR_RIGHT_BACKWARD = 24
ENABLE_LEFT = 22
ENABLE_RIGHT = 25

# --- Movement constants ---
MOTOR_SPEED = 75        # PWM duty cycle (0–100%)
TURN_TIME = 0.6         # seconds to complete a 90° turn
TURN_AROUND_TIME = 1.2  # seconds for 180° turn
STOP_DELAY = 0.1        # small delay for safety stop

class MotorController:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([MOTOR_LEFT_FORWARD, MOTOR_LEFT_BACKWARD,
                    MOTOR_RIGHT_FORWARD, MOTOR_RIGHT_BACKWARD,
                    ENABLE_LEFT, ENABLE_RIGHT], GPIO.OUT)

        self.pwm_left = GPIO.PWM(ENABLE_LEFT, 1000)
        self.pwm_right = GPIO.PWM(ENABLE_RIGHT, 1000)
        self.pwm_left.start(MOTOR_SPEED)
        self.pwm_right.start(MOTOR_SPEED)
        self.stop()

    # ------------------------
    #  Basic motor controls
    # ------------------------
    def set_speed(self, speed):
        """Change speed dynamically (0–100)."""
        global MOTOR_SPEED
        MOTOR_SPEED = max(0, min(speed, 100))
        self.pwm_left.ChangeDutyCycle(MOTOR_SPEED)
        self.pwm_right.ChangeDutyCycle(MOTOR_SPEED)
        print(f"Speed set to {MOTOR_SPEED}%")

    def forward(self, duration=None):
        GPIO.output(MOTOR_LEFT_FORWARD, True)
        GPIO.output(MOTOR_LEFT_BACKWARD, False)
        GPIO.output(MOTOR_RIGHT_FORWARD, True)
        GPIO.output(MOTOR_RIGHT_BACKWARD, False)
        print("Moving forward")
        if duration:
            time.sleep(duration)
            self.stop()

    def backward(self, duration=None):
        GPIO.output(MOTOR_LEFT_FORWARD, False)
        GPIO.output(MOTOR_LEFT_BACKWARD, True)
        GPIO.output(MOTOR_RIGHT_FORWARD, False)
        GPIO.output(MOTOR_RIGHT_BACKWARD, True)
        print("Reversing")
        if duration:
            time.sleep(duration)
            self.stop()

    def turn_left(self, duration=TURN_TIME):
        GPIO.output(MOTOR_LEFT_FORWARD, False)
        GPIO.output(MOTOR_LEFT_BACKWARD, True)
        GPIO.output(MOTOR_RIGHT_FORWARD, True)
        GPIO.output(MOTOR_RIGHT_BACKWARD, False)
        print("Turning left")
        time.sleep(duration)
        self.stop()

    def turn_right(self, duration=TURN_TIME):
        GPIO.output(MOTOR_LEFT_FORWARD, True)
        GPIO.output(MOTOR_LEFT_BACKWARD, False)
        GPIO.output(MOTOR_RIGHT_FORWARD, False)
        GPIO.output(MOTOR_RIGHT_BACKWARD, True)
        print("Turning right")
        time.sleep(duration)
        self.stop()

    def turn_around(self):
        print("Turning around (180°)")
        self.turn_left(duration=TURN_AROUND_TIME)
        self.stop()

    def stop(self):
        GPIO.output(MOTOR_LEFT_FORWARD, False)
        GPIO.output(MOTOR_LEFT_BACKWARD, False)
        GPIO.output(MOTOR_RIGHT_FORWARD, False)
        GPIO.output(MOTOR_RIGHT_BACKWARD, False)
        time.sleep(STOP_DELAY)
        print("Motors stopped")

    def cleanup(self):
        """Stop PWM and clean GPIO."""
        self.stop()
        self.pwm_left.stop()
        self.pwm_right.stop()
        GPIO.cleanup()
        print("GPIO cleaned up")

# ------------------------
#  Example test run
# ------------------------
if __name__ == "__main__":
    try:
        motor = MotorController()
        motor.forward(1)
        motor.turn_left()
        motor.forward(1)
        motor.turn_right()
        motor.turn_around()
        motor.backward(1)
        motor.stop()
    except KeyboardInterrupt:
        pass
    finally:
        motor.cleanup()
