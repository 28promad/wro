# motor_control.py
# Motor controller for the rover with movement state tracking

import RPi.GPIO as GPIO
import time

class MotorController:
    """Controls the rover's motors with L298N motor driver."""
    
    def __init__(self, left_pins=(21, 20, 16), right_pins=(26, 12, 1), default_speed=35):
        """
        Initialize motor controller.
        
        Args:
            left_pins: (enable, in1, in2) for left motor
            right_pins: (enable, in1, in2) for right motor
            default_speed: PWM duty cycle (0-100)
        """
        # Pin assignments
        self.left_enable, self.left_in1, self.left_in2 = left_pins
        self.right_enable, self.right_in1, self.right_in2 = right_pins
        
        self.default_speed = default_speed
        self._current_speed = default_speed
        self._is_moving = False
        self._movement_start_time = 0
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins
        for pin in [self.left_in1, self.left_in2, self.right_in1, self.right_in2]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, False)
        
        # Setup PWM for speed control
        GPIO.setup(self.left_enable, GPIO.OUT)
        GPIO.setup(self.right_enable, GPIO.OUT)
        
        self.left_pwm = GPIO.PWM(self.left_enable, 1000)  # 1kHz frequency
        self.right_pwm = GPIO.PWM(self.right_enable, 1000)
        
        self.left_pwm.start(0)
        self.right_pwm.start(0)
        
        print("✓ Motor controller initialized")
    
    def set_speed(self, speed):
        """Set motor speed (0-100)."""
        self._current_speed = max(0, min(100, speed))
        if self._is_moving:
            self.left_pwm.ChangeDutyCycle(self._current_speed)
            self.right_pwm.ChangeDutyCycle(self._current_speed)
    
    def forward(self, duration=None):
        """Move forward. If duration specified, move for that many seconds."""
        self._is_moving = True
        self._movement_start_time = time.time()
        
        # Left motor forward
        GPIO.output(self.left_in1, True)
        GPIO.output(self.left_in2, False)
        
        # Right motor forward
        GPIO.output(self.right_in1, True)
        GPIO.output(self.right_in2, False)
        
        self.left_pwm.ChangeDutyCycle(self._current_speed)
        self.right_pwm.ChangeDutyCycle(self._current_speed)
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def backward(self, duration=None):
        """Move backward. If duration specified, move for that many seconds."""
        self._is_moving = True
        self._movement_start_time = time.time()
        
        # Left motor backward
        GPIO.output(self.left_in1, False)
        GPIO.output(self.left_in2, True)
        
        # Right motor backward
        GPIO.output(self.right_in1, False)
        GPIO.output(self.right_in2, True)
        
        self.left_pwm.ChangeDutyCycle(self._current_speed)
        self.right_pwm.ChangeDutyCycle(self._current_speed)
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def turn_left(self, duration=0.5):
        """Turn left for specified duration."""
        self._is_moving = False  # Turning doesn't count as forward movement
        
        # Left motor backward
        GPIO.output(self.left_in1, False)
        GPIO.output(self.left_in2, True)
        
        # Right motor forward
        GPIO.output(self.right_in1, True)
        GPIO.output(self.right_in2, False)
        
        self.left_pwm.ChangeDutyCycle(self._current_speed)
        self.right_pwm.ChangeDutyCycle(self._current_speed)
        
        time.sleep(duration)
        self.stop()
    
    def turn_right(self, duration=0.5):
        """Turn right for specified duration."""
        self._is_moving = False
        
        # Left motor forward
        GPIO.output(self.left_in1, True)
        GPIO.output(self.left_in2, False)
        
        # Right motor backward
        GPIO.output(self.right_in1, False)
        GPIO.output(self.right_in2, True)
        
        self.left_pwm.ChangeDutyCycle(self._current_speed)
        self.right_pwm.ChangeDutyCycle(self._current_speed)
        
        time.sleep(duration)
        self.stop()
    
    def stop(self):
        """Stop all motors."""
        self._is_moving = False
        
        GPIO.output(self.left_in1, False)
        GPIO.output(self.left_in2, False)
        GPIO.output(self.right_in1, False)
        GPIO.output(self.right_in2, False)
        
        self.left_pwm.ChangeDutyCycle(0)
        self.right_pwm.ChangeDutyCycle(0)
    
    def cleanup(self):
        """Cleanup GPIO and stop motors."""
        self.stop()
        self.left_pwm.stop()
        self.right_pwm.stop()
        GPIO.cleanup()
    
    def __del__(self):
        """Destructor - ensure motors are stopped."""
        try:
            self.cleanup()
        except Exception:
            pass