#!/usr/bin/env python3
# test_ultrasonic.py
# Test tool for HC-SR04 ultrasonic sensors
# Compatible with Raspberry Pi 4B and Pi 5

import time
import sys
import os

# Try to import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    print("✓ RPi.GPIO imported successfully")
except ImportError:
    print("❌ Error: RPi.GPIO not found")
    print("Install with: sudo apt-get install python3-rpi.gpio")
    sys.exit(1)

# Check Pi version
try:
    with open('/proc/cpuinfo', 'r') as f:
        cpuinfo = f.read()
        if 'BCM2711' in cpuinfo:
            pi_model = "Raspberry Pi 4"
        elif 'BCM2712' in cpuinfo:
            pi_model = "Raspberry Pi 5"
        else:
            pi_model = "Unknown Raspberry Pi"
    print(f"✓ Detected: {pi_model}")
except Exception as e:
    print(f"⚠️  Could not detect Pi model: {e}")
    pi_model = "Unknown"

print("")

# ---------------- Configuration ----------------
# Front sensors (for forward navigation)
ULTRASONIC_FRONT = {
    "front_left":   (15, 14),
    "front_center": (23, 18),
    "front_right":  (25, 24)
}

# Rear sensors (for return navigation) - DISABLED FOR TESTING
ULTRASONIC_REAR = {
    # "rear_left":    (17, 27),
    # "rear_center":  (23, 24),
    # "rear_right":   (25, 8)
}

# Use only front sensors for testing
ALL_SENSORS = {**ULTRASONIC_FRONT}  # Only front 3 sensors
# ALL_SENSORS = {**ULTRASONIC_FRONT, **ULTRASONIC_REAR}  # Uncomment for all 6

# ---------------- GPIO Setup ----------------
def setup_gpio():
    """Initialize GPIO for ultrasonic sensors."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for name, (trig, echo) in ALL_SENSORS.items():
        try:
            GPIO.setup(trig, GPIO.OUT)
            GPIO.setup(echo, GPIO.IN)
            GPIO.output(trig, False)
        except Exception as e:
            print(f"❌ Error setting up {name} (GPIO {trig},{echo}): {e}")
            return False
    
    print("✓ All GPIO pins configured")
    return True

# ---------------- Distance Measurement ----------------
def measure_distance(trig, echo, timeout=0.04):
    """
    Measure distance using HC-SR04 sensor.
    
    Args:
        trig: Trigger pin (BCM numbering)
        echo: Echo pin (BCM numbering)
        timeout: Max time to wait for response (seconds)
    
    Returns:
        Distance in cm, or None if timeout/error
    """
    try:
        # Send trigger pulse
        GPIO.output(trig, True)
        time.sleep(0.00001)  # 10 microseconds
        GPIO.output(trig, False)
        
        # Wait for echo start
        start_time = time.time()
        timeout_time = start_time + timeout
        
        while GPIO.input(echo) == 0:
            start_time = time.time()
            if start_time > timeout_time:
                return None
        
        # Wait for echo end
        end_time = time.time()
        while GPIO.input(echo) == 1:
            end_time = time.time()
            if end_time > timeout_time:
                return None
        
        # Calculate distance
        duration = end_time - start_time
        distance = (duration * 34300) / 2  # Speed of sound = 343 m/s
        
        return distance
    
    except Exception as e:
        print(f"⚠️  Measurement error: {e}")
        return None

# ---------------- Test Functions ----------------
def test_single_sensor(name, trig, echo, samples=5):
    """Test a single sensor with multiple samples."""
    print(f"\nTesting {name} (Trig: GPIO {trig}, Echo: GPIO {echo})")
    print("-" * 50)
    
    readings = []
    errors = 0
    
    for i in range(samples):
        dist = measure_distance(trig, echo)
        
        if dist is not None:
            readings.append(dist)
            status = "✓" if 2 <= dist <= 400 else "⚠️"
            print(f"  Sample {i+1}: {dist:6.1f} cm {status}")
        else:
            errors += 1
            print(f"  Sample {i+1}: TIMEOUT/ERROR ❌")
        
        time.sleep(0.1)
    
    # Statistics
    if readings:
        avg = sum(readings) / len(readings)
        min_dist = min(readings)
        max_dist = max(readings)
        
        print(f"\n  Average: {avg:.1f} cm")
        print(f"  Range:   {min_dist:.1f} - {max_dist:.1f} cm")
        print(f"  Success: {len(readings)}/{samples}")
        
        # Interpretation
        if avg < 2:
            print("  ⚠️  Too close - sensor may be blocked")
        elif avg > 400:
            print("  ⚠️  Out of range - nothing detected")
        elif errors == 0:
            print("  ✓ Sensor working properly!")
        else:
            print(f"  ⚠️  {errors} errors detected")
    else:
        print("  ❌ All measurements failed!")
    
    return len(readings) > 0

def test_all_sensors_once():
    """Read all 6 sensors once and display results."""
    print("\nReading all sensors...")
    print("-" * 70)
    print(f"{'Sensor':<15} {'Position':<12} {'Distance':<10} {'Status'}")
    print("-" * 70)
    
    for name, (trig, echo) in ALL_SENSORS.items():
        dist = measure_distance(trig, echo)
        
        position = name.replace('_', ' ').title()
        
        if dist is not None:
            if 2 <= dist <= 400:
                status = "✓ OK"
                dist_str = f"{dist:.1f} cm"
            elif dist < 2:
                status = "⚠️  Too close"
                dist_str = f"{dist:.1f} cm"
            else:
                status = "⚠️  Out of range"
                dist_str = f"{dist:.1f} cm"
        else:
            dist_str = "TIMEOUT"
            status = "❌ Error"
        
        print(f"{name:<15} {position:<12} {dist_str:<10} {status}")

def continuous_monitoring():
    """Continuously monitor all sensors (like rover operation)."""
    print("\nContinuous Monitoring Mode")
    print("This simulates how sensors work during rover operation")
    print("Press Ctrl+C to stop\n")
    print("-" * 70)
    
    try:
        while True:
            # Clear line for updating display
            print("\r" + " " * 70 + "\r", end="")
            
            readings = []
            for name, (trig, echo) in ALL_SENSORS.items():
                dist = measure_distance(trig, echo)
                if dist is not None:
                    readings.append(f"{name}: {dist:5.1f}cm")
                else:
                    readings.append(f"{name}: ERROR")
            
            print("\r" + " | ".join(readings[:3]), end="")
            print("\n" + " | ".join(readings[3:]), end="")
            print("\033[F", end="")  # Move cursor up
            
            time.sleep(0.2)
    
    except KeyboardInterrupt:
        print("\n\n✓ Monitoring stopped")

def visual_display():
    """Visual bar graph display of sensor readings."""
    print("\nVisual Display Mode")
    print("Shows distance as horizontal bars")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            os.system('clear' if os.name != 'nt' else 'cls')
            print("╔════════════════════════════════════════════════════════╗")
            print("║          ULTRASONIC SENSOR VISUAL DISPLAY             ║")
            print("╚════════════════════════════════════════════════════════╝\n")
            
            for name, (trig, echo) in ALL_SENSORS.items():
                dist = measure_distance(trig, echo)
                
                # Create bar graph (0-100cm range)
                if dist is not None and dist <= 100:
                    bar_length = int(dist / 2)  # Scale to 50 chars max
                    bar = "█" * bar_length
                    print(f"{name:15} [{dist:5.1f}cm] {bar}")
                elif dist is not None:
                    print(f"{name:15} [{dist:5.1f}cm] ▓▓▓▓▓ (out of range)")
                else:
                    print(f"{name:15} [ ERROR ] ❌")
                
                time.sleep(0.01)
            
            print("\n[Press Ctrl+C to exit]")
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\n✓ Display stopped")

def obstacle_detection_test():
    """Test obstacle detection logic (like rover_control.py)."""
    print("\nObstacle Detection Test")
    print("Simulates rover obstacle avoidance logic")
    print("Threshold: 15 cm")
    print("Press Ctrl+C to stop\n")
    
    OBSTACLE_DIST = 15.0
    
    try:
        while True:
            time.sleep(0.5)
            
            # Test front sensors
            print("\n--- FRONT SENSORS ---")
            front_readings = {}
            for name, (trig, echo) in ULTRASONIC_FRONT.items():
                dist = measure_distance(trig, echo)
                front_readings[name] = dist if dist is not None else float('inf')
                print(f"{name}: {front_readings[name]:.1f} cm")
            
            # Decision logic
            left = front_readings.get('front_left', float('inf'))
            center = front_readings.get('front_center', float('inf'))
            right = front_readings.get('front_right', float('inf'))
            
            print("\n💡 Decision:", end=" ")
            
            if center < OBSTACLE_DIST:
                if left > right:
                    print(f"🚧 Obstacle ahead! Turn LEFT (L:{left:.1f} > R:{right:.1f})")
                else:
                    print(f"🚧 Obstacle ahead! Turn RIGHT (R:{right:.1f} > L:{left:.1f})")
            elif left < OBSTACLE_DIST:
                print(f"🚧 Obstacle on left! Adjust RIGHT ({left:.1f} cm)")
            elif right < OBSTACLE_DIST:
                print(f"🚧 Obstacle on right! Adjust LEFT ({right:.1f} cm)")
            else:
                print("✓ Clear path - FORWARD")
    
    except KeyboardInterrupt:
        print("\n\n✓ Test stopped")

# ---------------- Pin Test ----------------
def test_gpio_pins():
    """Test if GPIO pins can be accessed."""
    print("\nGPIO Pin Access Test")
    print("-" * 50)
    
    test_pins = [5, 6, 13, 19, 26, 21, 17, 27, 23, 24, 25, 8]
    
    for pin in test_pins:
        try:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, False)
            print(f"  GPIO {pin:2d}: ✓ OK")
        except Exception as e:
            print(f"  GPIO {pin:2d}: ❌ ERROR - {e}")
    
    print("\n✓ Pin access test complete")

# ---------------- Wiring Guide ----------------
def show_wiring_guide():
    """Display wiring guide for all sensors."""
    print("\n" + "="*70)
    print("                    WIRING GUIDE")
    print("="*70)
    print("\nEach HC-SR04 sensor has 4 pins: VCC, GND, Trig, Echo")
    print("\n⚠️  IMPORTANT: Echo pin needs 1kΩ resistor for voltage divider!")
    print("   (5V -> 1kΩ resistor -> Echo pin -> GPIO)")
    print("\n" + "-"*70)
    print(f"{'Sensor':<15} {'Trig Pin':<12} {'Echo Pin':<12} {'VCC/GND'}")
    print("-"*70)
    
    for name, (trig, echo) in ALL_SENSORS.items():
        print(f"{name:<15} GPIO {trig:<8} GPIO {echo:<8} 5V / GND")
    
    print("-"*70)
    print("\nPower Connections:")
    print("  VCC → Raspberry Pi 5V (Pin 2 or 4)")
    print("  GND → Raspberry Pi GND (Pin 6, 9, 14, 20, 25, 30, 34, or 39)")
    print("\n" + "="*70)

# ---------------- Main Menu ----------------
def main_menu():
    """Display main test menu."""
    while True:
        print("\n" + "="*70)
        print("           🔍 ULTRASONIC SENSOR TEST TOOL")
        print("="*70)
        print("\n1. Test Single Sensor (detailed)")
        print("2. Test All Sensors (quick scan)")
        print("3. Continuous Monitoring")
        print("4. Visual Display (bar graph)")
        print("5. Obstacle Detection Test")
        print("6. GPIO Pin Access Test")
        print("7. Show Wiring Guide")
        print("8. Exit")
        print("\n" + "-"*70)
        
        choice = input("\nSelect option [1-8]: ").strip()
        
        if choice == "1":
            print("\n" + "="*70)
            print("           TEST SINGLE SENSOR")
            print("="*70)
            print("\nAvailable sensors:")
            for i, name in enumerate(ALL_SENSORS.keys(), 1):
                print(f"  {i}. {name}")
            
            sensor_choice = input("\nSelect sensor [1-6]: ").strip()
            try:
                sensor_idx = int(sensor_choice) - 1
                sensor_name = list(ALL_SENSORS.keys())[sensor_idx]
                trig, echo = ALL_SENSORS[sensor_name]
                test_single_sensor(sensor_name, trig, echo, samples=10)
            except (ValueError, IndexError):
                print("❌ Invalid selection")
        
        elif choice == "2":
            test_all_sensors_once()
        
        elif choice == "3":
            continuous_monitoring()
        
        elif choice == "4":
            visual_display()
        
        elif choice == "5":
            obstacle_detection_test()
        
        elif choice == "6":
            test_gpio_pins()
        
        elif choice == "7":
            show_wiring_guide()
        
        elif choice == "8":
            print("\n👋 Exiting...")
            break
        
        else:
            print("❌ Invalid option")

# ---------------- Entry Point ----------------
if __name__ == "__main__":
    print("="*70)
    print("           🔍 ULTRASONIC SENSOR TEST TOOL")
    print("           Compatible with Pi 4B and Pi 5")
    print("="*70)
    print("")
    
    try:
        if not setup_gpio():
            print("\n❌ GPIO setup failed. Check connections and try again.")
            sys.exit(1)
        
        main_menu()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    
    finally:
        GPIO.cleanup()
        print("✓ GPIO cleanup complete")