#!/usr/bin/env python3
# test_ultrasonic.py
# Test tool for HC-SR04 ultrasonic sensors using gpiozero
# Compatible with Raspberry Pi 4B and Pi 5

import time
import sys
import os
from gpiozero import DistanceSensor

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

print("✓ Using gpiozero for GPIO control")
print("")

# ---------------- Configuration ----------------
# Front sensors (for forward navigation)
ULTRASONIC_FRONT = {
    "front_left":   (23, 18),   # (trigger, echo)
    "front_center": (24, 25),
    "front_right":  (3, 2)
}

# Rear sensors (for return navigation)
ULTRASONIC_REAR = {
    "rear_center":  (24, 25)
}

ALL_SENSORS = {**ULTRASONIC_FRONT, **ULTRASONIC_REAR}

# Sensor configuration
MAX_DISTANCE = 4.0      # meters (4m max range)
THRESHOLD_DISTANCE = 0.2  # meters (20cm for obstacle detection)

# ---------------- Sensor Setup ----------------
def setup_sensors():
    """Initialize all ultrasonic sensors using gpiozero."""
    sensors = {}
    
    print("Initializing sensors...")
    for name, (trig, echo) in ALL_SENSORS.items():
        try:
            sensor = DistanceSensor(
                echo=echo,
                trigger=trig,
                max_distance=MAX_DISTANCE,
                threshold_distance=THRESHOLD_DISTANCE
            )
            sensors[name] = sensor
            print(f"  ✓ {name:<15} (Trig: GPIO {trig}, Echo: GPIO {echo})")
        except Exception as e:
            print(f"  ❌ {name:<15} ERROR: {e}")
    
    print(f"\n✓ {len(sensors)}/{len(ALL_SENSORS)} sensors initialized")
    return sensors

# ---------------- Test Functions ----------------
def test_single_sensor(name, sensor, samples=5):
    """Test a single sensor with multiple samples."""
    print(f"\nTesting {name}")
    print("-" * 50)
    
    readings = []
    errors = 0
    
    for i in range(samples):
        try:
            dist = sensor.distance  # Returns distance in meters
            dist_cm = dist * 100    # Convert to cm for display
            readings.append(dist_cm)
            status = "✓" if 2 <= dist_cm <= 400 else "⚠️"
            print(f"  Sample {i+1}: {dist_cm:6.1f} cm ({dist:.3f} m) {status}")
        except Exception as e:
            errors += 1
            print(f"  Sample {i+1}: ERROR - {e} ❌")
        
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

def test_all_sensors_once(sensors):
    """Read all sensors once and display results."""
    print("\nReading all sensors...")
    print("-" * 70)
    print(f"{'Sensor':<15} {'Position':<12} {'Distance (cm)':<15} {'Status'}")
    print("-" * 70)
    
    for name, sensor in sensors.items():
        try:
            dist = sensor.distance  # meters
            dist_cm = dist * 100
            
            position = name.replace('_', ' ').title()
            
            if 2 <= dist_cm <= 400:
                status = "✓ OK"
            elif dist_cm < 2:
                status = "⚠️  Too close"
            else:
                status = "⚠️  Out of range"
            
            print(f"{name:<15} {position:<12} {dist_cm:6.1f} cm      {status}")
        
        except Exception as e:
            position = name.replace('_', ' ').title()
            print(f"{name:<15} {position:<12} ERROR          ❌")

def continuous_monitoring(sensors):
    """Continuously monitor all sensors."""
    print("\nContinuous Monitoring Mode")
    print("Press Ctrl+C to stop\n")
    print("-" * 70)
    
    try:
        while True:
            readings = []
            for name, sensor in sensors.items():
                try:
                    dist = sensor.distance * 100  # Convert to cm
                    readings.append(f"{name}: {dist:5.1f}cm")
                except Exception:
                    readings.append(f"{name}: ERROR")
            
            # Print on same line
            print("\r" + " | ".join(readings), end="", flush=True)
            time.sleep(0.2)
    
    except KeyboardInterrupt:
        print("\n\n✓ Monitoring stopped")

def visual_display(sensors):
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
            
            for name, sensor in sensors.items():
                try:
                    dist = sensor.distance * 100  # Convert to cm
                    
                    # Create bar graph (0-100cm range)
                    if dist <= 100:
                        bar_length = int(dist / 2)  # Scale to 50 chars max
                        bar = "█" * bar_length
                        print(f"{name:15} [{dist:5.1f}cm] {bar}")
                    else:
                        print(f"{name:15} [{dist:5.1f}cm] ▓▓▓▓▓ (out of range)")
                except Exception:
                    print(f"{name:15} [ ERROR ] ❌")
                
                time.sleep(0.01)
            
            print("\n[Press Ctrl+C to exit]")
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\n✓ Display stopped")

def obstacle_detection_test(sensors):
    """Test obstacle detection logic."""
    print("\nObstacle Detection Test")
    print("Simulates rover obstacle avoidance logic")
    print("Threshold: 20 cm")
    print("Press Ctrl+C to stop\n")
    
    OBSTACLE_DIST = 0.20  # 20cm in meters
    
    try:
        while True:
            time.sleep(0.5)
            
            # Test front sensors
            print("\n--- FRONT SENSORS ---")
            front_readings = {}
            
            for name in ['front_left', 'front_center', 'front_right']:
                if name in sensors:
                    try:
                        dist = sensors[name].distance  # meters
                        front_readings[name] = dist
                        print(f"{name}: {dist*100:.1f} cm")
                    except Exception:
                        front_readings[name] = float('inf')
                        print(f"{name}: ERROR")
            
            # Decision logic
            left = front_readings.get('front_left', float('inf'))
            center = front_readings.get('front_center', float('inf'))
            right = front_readings.get('front_right', float('inf'))
            
            print("\n💡 Decision:", end=" ")
            
            if center < OBSTACLE_DIST:
                if left > right:
                    print(f"🚧 Obstacle ahead! Turn LEFT (L:{left*100:.1f} > R:{right*100:.1f})")
                else:
                    print(f"🚧 Obstacle ahead! Turn RIGHT (R:{right*100:.1f} > L:{left*100:.1f})")
            elif left < OBSTACLE_DIST:
                print(f"🚧 Obstacle on left! Adjust RIGHT ({left*100:.1f} cm)")
            elif right < OBSTACLE_DIST:
                print(f"🚧 Obstacle on right! Adjust LEFT ({right*100:.1f} cm)")
            else:
                print("✓ Clear path - FORWARD")
    
    except KeyboardInterrupt:
        print("\n\n✓ Test stopped")

# ---------------- Wiring Guide ----------------
def show_wiring_guide():
    """Display wiring guide for all sensors."""
    print("\n" + "="*70)
    print("                    WIRING GUIDE")
    print("="*70)
    print("\nEach HC-SR04 sensor has 4 pins: VCC, GND, Trig, Echo")
    print("\n⚠️  IMPORTANT: With gpiozero, no resistor needed on Echo pin!")
    print("   gpiozero handles voltage level conversion automatically")
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
    sensors = setup_sensors()
    
    if not sensors:
        print("\n❌ No sensors initialized. Check wiring and try again.")
        return
    
    while True:
        print("\n" + "="*70)
        print("           🔍 ULTRASONIC SENSOR TEST TOOL (gpiozero)")
        print("="*70)
        print("\n1. Test Single Sensor (detailed)")
        print("2. Test All Sensors (quick scan)")
        print("3. Continuous Monitoring")
        print("4. Visual Display (bar graph)")
        print("5. Obstacle Detection Test")
        print("6. Show Wiring Guide")
        print("7. Exit")
        print("\n" + "-"*70)
        
        choice = input("\nSelect option [1-7]: ").strip()
        
        if choice == "1":
            print("\n" + "="*70)
            print("           TEST SINGLE SENSOR")
            print("="*70)
            print("\nAvailable sensors:")
            sensor_list = list(sensors.keys())
            for i, name in enumerate(sensor_list, 1):
                print(f"  {i}. {name}")
            
            sensor_choice = input("\nSelect sensor [1-{}]: ".format(len(sensor_list))).strip()
            try:
                sensor_idx = int(sensor_choice) - 1
                sensor_name = sensor_list[sensor_idx]
                test_single_sensor(sensor_name, sensors[sensor_name], samples=10)
            except (ValueError, IndexError):
                print("❌ Invalid selection")
        
        elif choice == "2":
            test_all_sensors_once(sensors)
        
        elif choice == "3":
            continuous_monitoring(sensors)
        
        elif choice == "4":
            visual_display(sensors)
        
        elif choice == "5":
            obstacle_detection_test(sensors)
        
        elif choice == "6":
            show_wiring_guide()
        
        elif choice == "7":
            print("\n👋 Exiting...")
            break
        
        else:
            print("❌ Invalid option")
    
    # Cleanup
    print("\nCleaning up sensors...")
    for sensor in sensors.values():
        sensor.close()
    print("✓ Cleanup complete")

# ---------------- Entry Point ----------------
if __name__ == "__main__":
    print("="*70)
    print("           🔍 ULTRASONIC SENSOR TEST TOOL")
    print("           Using gpiozero - Pi 4B and Pi 5 compatible")
    print("="*70)
    print("")
    
    try:
        main_menu()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("✓ Exiting")