import RPi.GPIO as GPIO
from time import sleep

class MotorController:
    def __init__(self, right_motor_pins=(17, 27, 4), left_motor_pins=(5, 6, 13), initial_speed=75):
        """
        Initialize the motor controller.
        
        Parameters:
        right_motor_pins: tuple (in1, in2, enable) for right motor
        left_motor_pins: tuple (in3, in4, enable) for left motor
        initial_speed: PWM duty cycle (0-100) for both motors
        """
        # Store pin numbers
        self.in1, self.in2, self.en_a = right_motor_pins
        self.in3, self.in4, self.en_b = left_motor_pins
        
        # Setup GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        
        # Setup all pins as outputs
        for pin in [self.in1, self.in2, self.en_a, self.in3, self.in4, self.en_b]:
            GPIO.setup(pin, GPIO.OUT)
            
        # Setup PWM for speed control
        self.right_pwm = GPIO.PWM(self.en_a, 100)  # 100Hz frequency
        self.left_pwm = GPIO.PWM(self.en_b, 100)
        
        # Start PWM
        self.right_pwm.start(initial_speed)
        self.left_pwm.start(initial_speed)
        
        # Stop motors initially
        self.stop()
    
    def set_speeds(self, right_speed, left_speed):
        """Set individual motor speeds (0-100)"""
        self.right_pwm.ChangeDutyCycle(max(0, min(100, right_speed)))
        self.left_pwm.ChangeDutyCycle(max(0, min(100, left_speed)))
    
    def forward(self, speed=None):
        """Move forward"""
        GPIO.output(self.in1, GPIO.HIGH)
        GPIO.output(self.in2, GPIO.LOW)
        GPIO.output(self.in3, GPIO.HIGH)
        GPIO.output(self.in4, GPIO.LOW)
        if speed is not None:
            self.set_speeds(speed, speed)
    
    def backward(self, speed=None):
        """Move backward"""
        GPIO.output(self.in1, GPIO.LOW)
        GPIO.output(self.in2, GPIO.HIGH)
        GPIO.output(self.in3, GPIO.LOW)
        GPIO.output(self.in4, GPIO.HIGH)
        if speed is not None:
            self.set_speeds(speed, speed)
    
    def turn_left(self, speed=75):
        """Turn left (rotate counterclockwise)"""
        GPIO.output(self.in1, GPIO.HIGH)  # Right motor forward
        GPIO.output(self.in2, GPIO.LOW)
        GPIO.output(self.in3, GPIO.LOW)   # Left motor backward/stop
        GPIO.output(self.in4, GPIO.HIGH)
        if speed is not None:
            self.set_speeds(speed, speed)
    
    def turn_right(self, speed=75):
        """Turn right (rotate clockwise)"""
        GPIO.output(self.in1, GPIO.LOW)    # Right motor backward/stop
        GPIO.output(self.in2, GPIO.HIGH)
        GPIO.output(self.in3, GPIO.HIGH)   # Left motor forward
        GPIO.output(self.in4, GPIO.LOW)
        if speed is not None:
            self.set_speeds(speed, speed)
    
    def stop(self):
        """Stop all motors"""
        GPIO.output(self.in1, GPIO.LOW)
        GPIO.output(self.in2, GPIO.LOW)
        GPIO.output(self.in3, GPIO.LOW)
        GPIO.output(self.in4, GPIO.LOW)
    
    def cleanup(self):
        """Clean up GPIO (call this when done)"""
        self.stop()
        self.right_pwm.stop()
        self.left_pwm.stop()
        GPIO.cleanup()

# Example usage (only runs if this file is run directly)
if __name__ == "__main__":
    try:
        # Create motor controller with default pin numbers
        motors = MotorController()
        
        print("Motor Control Ready")
        print("Commands: w=forward, s=backward, a=left, d=right, c=stop, q=quit")
        
        while True:
            command = input().lower()
            
            if command == 'w':
                motors.forward()
                print("Forward")
            elif command == 's':
                motors.backward()
                print("Backward")
            elif command == 'a':
                motors.turn_left()
                print("Left")
            elif command == 'd':
                motors.turn_right()
                print("Right")
            elif command == 'c':
                motors.stop()
                print("Stop")
            elif command == 'q':
                print("Quitting...")
                break
                
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
    finally:
        motors.cleanup()
        print("GPIO cleaned up")