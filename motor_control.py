# motor_control.py
# Motor controller for the rover using gpiozero Motor (L298N)
# Replaces manual RPi.GPIO usage with gpiozero abstractions.

from gpiozero import Motor
from time import sleep

class MotorController:
    """Controls the rover's motors using gpiozero Motor objects (L298N)."""

    def __init__(self, left_pins=(21, 20, 16), right_pins=(26, 12, 1), default_speed=35):
        """
        Args:
            left_pins:  (enable_pin, in1_pin, in2_pin)
            right_pins: (enable_pin, in1_pin, in2_pin)
            default_speed: PWM duty cycle percent (0-100)
        """
        # Map input format (enable, in1, in2) -> Motor(forward=in1, backward=in2, enable=enable)
        left_enable, left_in1, left_in2 = left_pins
        right_enable, right_in1, right_in2 = right_pins

        # gpiozero Motor: forward, backward, optional enable. pwm=True for speed control.
        self.left_motor = Motor(forward=left_in1, backward=left_in2, enable=left_enable, pwm=True)
        self.right_motor = Motor(forward=right_in1, backward=right_in2, enable=right_enable, pwm=True)

        # Speed stored as 0.0 - 1.0 internally; user API remains 0-100.
        self._speed_percent = max(0, min(100, default_speed))
        self.speed = self._speed_percent / 100.0

        # Movement state
        self._is_moving = False
        self._last_command = None  # 'forward', 'backward', 'turn_left', 'turn_right', None

        print("✓ gpiozero MotorController initialized")

    # ---------- Speed API ----------
    def set_speed(self, speed):
        """Set motor speed as percent (0-100). Reapplies current motion if active."""
        self._speed_percent = max(0, min(100, int(speed)))
        self.speed = self._speed_percent / 100.0

        # Reapply current command to update running motors immediately
        if self._is_moving and self._last_command:
            if self._last_command == 'forward':
                self.left_motor.forward(self.speed)
                self.right_motor.forward(self.speed)
            elif self._last_command == 'backward':
                self.left_motor.backward(self.speed)
                self.right_motor.backward(self.speed)
            elif self._last_command == 'turn_left':
                self.left_motor.backward(self.speed)
                self.right_motor.forward(self.speed)
            elif self._last_command == 'turn_right':
                self.left_motor.forward(self.speed)
                self.right_motor.backward(self.speed)

    # ---------- Movements ----------
    def forward(self, duration=None):
        """Move forward. If duration provided, move for that many seconds."""
        self._is_moving = True
        self._last_command = 'forward'
        self.left_motor.forward(self.speed)
        self.right_motor.forward(self.speed)

        if duration:
            sleep(duration)
            self.stop()

    def backward(self, duration=None):
        """Move backward. If duration provided, move for that many seconds."""
        self._is_moving = True
        self._last_command = 'backward'
        self.left_motor.backward(self.speed)
        self.right_motor.backward(self.speed)

        if duration:
            sleep(duration)
            self.stop()

    def turn_left(self, duration=0.5):
        """Spin left (differential) for duration (seconds)."""
        # Turning is not considered forward movement in your code, keep _is_moving False
        self._is_moving = False
        self._last_command = 'turn_left'
        self.left_motor.backward(self.speed)
        self.right_motor.forward(self.speed)
        sleep(duration)
        self.stop()

    def turn_right(self, duration=0.5):
        """Spin right (differential) for duration (seconds)."""
        self._is_moving = False
        self._last_command = 'turn_right'
        self.left_motor.forward(self.speed)
        self.right_motor.backward(self.speed)
        sleep(duration)
        self.stop()

    def stop(self):
        """Stop both motors."""
        self._is_moving = False
        self._last_command = None
        try:
            self.left_motor.stop()
            self.right_motor.stop()
        except Exception:
            # gpiozero may raise when pins are in odd state; ignore gracefully
            pass

    # ---------- Cleanup ----------
    def cleanup(self):
        """Stop motors (gpiozero handles pin cleanup on program exit)."""
        self.stop()

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass
