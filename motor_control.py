# motor_control.py
# Motor controller for the rover using gpiozero

from gpiozero import Motor, OutputDevice
import time

class MotorController:
    """Controls the rover's motors with L298N motor driver using gpiozero."""
    
    def __init__(self, left_pins=(21, 20, 16), right_pins=(7, 12, 13), default_speed=0.4):
        """
        Initialize motor controller.
        
        Args:
            left_pins: (enable, in1, in2) for left motor
            right_pins: (enable, in1, in2) for right motor
            default_speed: Motor speed (0.0-1.0)
        """
        # Pin assignments
        left_enable, left_in1, left_in2 = left_pins
        right_enable, right_in1, right_in2 = right_pins
        
        self.default_speed = default_speed
        self._current_speed = default_speed
        self._is_moving = False
        self._movement_start_time = 0
        
        # Initialize motors using gpiozero
        # Motor(forward, backward, enable, pwm=True)
        self.left_motor = Motor(
            forward=left_in1,
            backward=left_in2,
            enable=left_enable,
            pwm=True
        )
        
        self.right_motor = Motor(
            forward=right_in1,
            backward=right_in2,
            enable=right_enable,
            pwm=True
        )
        
        print("✓ Motor controller initialized (gpiozero)")
    
    def set_speed(self, speed):
        """
        Set motor speed (0.0-1.0 or 0-100).
        Accepts both decimal (0.0-1.0) and percentage (0-100).
        """
        if speed > 1.0:
            # Assume percentage (0-100)
            speed = speed / 100.0
        
        self._current_speed = max(0.0, min(1.0, speed))
    
    def forward(self, duration=None):
        """Move forward. If duration specified, move for that many seconds."""
        self._is_moving = True
        self._movement_start_time = time.time()
        
        self.left_motor.forward(self._current_speed)
        self.right_motor.forward(self._current_speed)
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def backward(self, duration=None):
        """Move backward. If duration specified, move for that many seconds."""
        self._is_moving = True
        self._movement_start_time = time.time()
        
        self.left_motor.backward(self._current_speed)
        self.right_motor.backward(self._current_speed)
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def turn_left(self, duration=0.5):
        """Turn left for specified duration."""
        self._is_moving = False  # Turning doesn't count as forward movement
        
        # Left motor backward, right motor forward
        self.left_motor.backward(self._current_speed)
        self.right_motor.forward(self._current_speed)
        
        time.sleep(duration)
        self.stop()
    
    def turn_right(self, duration=0.5):
        """Turn right for specified duration."""
        self._is_moving = False
        
        # Left motor forward, right motor backward
        self.left_motor.forward(self._current_speed)
        self.right_motor.backward(self._current_speed)
        
        time.sleep(duration)
        self.stop()
    
    def stop(self):
        """Stop all motors."""
        self._is_moving = False
        
        self.left_motor.stop()
        self.right_motor.stop()
    
    def cleanup(self):
        """Cleanup motors."""
        self.stop()
        self.left_motor.close()
        self.right_motor.close()
    
    def __del__(self):
        """Destructor - ensure motors are stopped."""
        try:
            self.cleanup()
        except Exception:
            pass