# calibrate_odometry.py
# Tool to calibrate wheel speed and turn rate for accurate odometry

from motor_control import MotorController
import RPi.GPIO as GPIO
import time

def calibrate_forward_speed():
    """
    Calibrate forward movement speed.
    The rover will move forward for 5 seconds.
    Measure the actual distance traveled and input it.
    """
    print("\n" + "="*60)
    print("FORWARD SPEED CALIBRATION")
    print("="*60)
    print("\nInstructions:")
    print("1. Place a tape measure or ruler in front of the rover")
    print("2. Mark the starting position")
    print("3. The rover will move forward for 5 seconds")
    print("4. Measure how far it actually traveled")
    print("\nReady? Press ENTER to start...")
    input()
    
    motor = MotorController()
    motor.set_speed(75)  # Default speed
    
    print("\n🚗 Moving forward for 5 seconds...")
    print("(Mark the ending position!)")
    
    motor.forward(duration=5.0)
    
    print("\n✓ Movement complete!")
    
    actual_distance = float(input("Enter actual distance traveled (in meters): "))
    calculated_speed = actual_distance / 5.0
    
    print(f"\n📊 Results:")
    print(f"   Time: 5.0 seconds")
    print(f"   Distance: {actual_distance:.3f} meters")
    print(f"   Calculated speed: {calculated_speed:.3f} m/s")
    print(f"\n   Update rover_control.py:")
    print(f"   WHEEL_SPEED = {calculated_speed:.3f}")
    
    motor.cleanup()
    return calculated_speed

def calibrate_turn_rate():
    """
    Calibrate turning rate.
    The rover will turn for 2 seconds.
    Estimate the angle turned and input it.
    """
    print("\n" + "="*60)
    print("TURN RATE CALIBRATION")
    print("="*60)
    print("\nInstructions:")
    print("1. Place the rover on a flat surface")
    print("2. Mark the starting orientation (use tape or draw a line)")
    print("3. The rover will turn right for 2 seconds")
    print("4. Estimate how many degrees it turned")
    print("   (Hint: 90° = quarter turn, 180° = half turn, 360° = full turn)")
    print("\nReady? Press ENTER to start...")
    input()
    
    motor = MotorController()
    motor.set_speed(75)
    
    print("\n🔄 Turning right for 2 seconds...")
    print("(Observe the angle!)")
    
    motor.turn_right(duration=2.0)
    
    print("\n✓ Turn complete!")
    
    actual_angle = float(input("Enter actual angle turned (in degrees): "))
    calculated_rate = actual_angle / 2.0
    
    print(f"\n📊 Results:")
    print(f"   Time: 2.0 seconds")
    print(f"   Angle: {actual_angle:.1f} degrees")
    print(f"   Calculated turn rate: {calculated_rate:.1f} deg/s")
    print(f"\n   Update rover_control.py:")
    print(f"   TURN_RATE = {calculated_rate:.1f}")
    
    motor.cleanup()
    return calculated_rate

def calibrate_wheel_circumference():
    """
    Measure wheel circumference for future use.
    """
    print("\n" + "="*60)
    print("WHEEL CIRCUMFERENCE MEASUREMENT")
    print("="*60)
    print("\nInstructions:")
    print("1. Measure the diameter of one wheel (in cm)")
    print("2. Or wrap a string around the wheel and measure that")
    print("")
    
    choice = input("Do you want to (1) enter diameter or (2) enter circumference? [1/2]: ")
    
    if choice == "1":
        diameter_cm = float(input("Enter wheel diameter (cm): "))
        circumference_m = (diameter_cm * 3.14159) / 100
    else:
        circumference_cm = float(input("Enter wheel circumference (cm): "))
        circumference_m = circumference_cm / 100
    
    print(f"\n📊 Results:")
    print(f"   Wheel circumference: {circumference_m:.4f} meters")
    print(f"\n   Update rover_control.py:")
    print(f"   WHEEL_CIRCUMFERENCE = {circumference_m:.4f}")
    
    return circumference_m

def run_test_pattern():
    """
    Run a test pattern to verify calibration.
    Square pattern: forward, turn 90°, repeat 4 times.
    """
    print("\n" + "="*60)
    print("CALIBRATION TEST - SQUARE PATTERN")
    print("="*60)
    print("\nThe rover will attempt to drive in a square:")
    print("- Forward 1 meter")
    print("- Turn right 90°")
    print("- Repeat 4 times")
    print("\nIf calibration is correct, it should return to the starting position.")
    print("\nReady? Press ENTER to start...")
    input()
    
    motor = MotorController()
    motor.set_speed(75)
    
    # Read calibrated values (you'll need to update these)
    wheel_speed = 0.15  # m/s (update with your calibrated value)
    turn_rate = 90.0    # deg/s (update with your calibrated value)
    
    print("\n🎯 Starting test pattern...")
    
    for i in range(4):
        print(f"\nSide {i+1}/4:")
        
        # Move forward 1 meter
        forward_time = 1.0 / wheel_speed
        print(f"  Moving forward for {forward_time:.2f}s (1m)")
        motor.forward(duration=forward_time)
        time.sleep(0.5)
        
        # Turn right 90 degrees
        turn_time = 90.0 / turn_rate
        print(f"  Turning right for {turn_time:.2f}s (90°)")
        motor.turn_right(duration=turn_time)
        time.sleep(0.5)
    
    print("\n✓ Test complete!")
    print("\nDid the rover return to approximately the starting position?")
    print("If not, your calibration values need adjustment.")
    
    motor.cleanup()

def main():
    """Main calibration menu."""
    print("\n" + "="*60)
    print("🔧 ROVER ODOMETRY CALIBRATION TOOL")
    print("="*60)
    print("\nThis tool helps you calibrate your rover for accurate navigation.")
    print("You should calibrate in this order:")
    print("\n1. Measure wheel circumference")
    print("2. Calibrate forward speed")
    print("3. Calibrate turn rate")
    print("4. Test with square pattern")
    print("5. Exit")
    
    try:
        while True:
            print("\n" + "-"*60)
            choice = input("\nSelect option [1-5]: ")
            
            if choice == "1":
                calibrate_wheel_circumference()
            elif choice == "2":
                calibrate_forward_speed()
            elif choice == "3":
                calibrate_turn_rate()
            elif choice == "4":
                run_test_pattern()
            elif choice == "5":
                print("\n👋 Exiting calibration tool")
                break
            else:
                print("❌ Invalid option")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted")
    finally:
        GPIO.cleanup()
        print("✓ Cleanup complete")

if __name__ == "__main__":
    main()