#!/usr/bin/env python3
# test_ultrasonic_gpiozero.py
# Test tool for HC-SR04 ultrasonic sensors using gpiozero
# Compatible with Raspberry Pi 4B and Pi 5

import time
import sys
import os

print("✓ Using gpiozero DistanceSensor instead of RPi.GPIO\n")

# gpiozero
try:
    from gpiozero import DistanceSensor
except ImportError:
    print("❌ ERROR: gpiozero not installed")
    print("Install with: sudo apt install python3-gpiozero")
    sys.exit(1)

# ---------------- Pi Version Check ----------------
try:
    with open('/proc/cpuinfo', 'r') as f:
        cpuinfo = f.read()
        if 'BCM2711' in cpuinfo:
            print("✓ Detected: Raspberry Pi 4")
        elif 'BCM2712' in cpuinfo:
            print("✓ Detected: Raspberry Pi 5")
        else:
            print("⚠️  Raspberry Pi model unknown")
except Exception as e:
    print(f"⚠️  Could not read /proc/cpuinfo: {e}")

print("")
# trig echo
# ---------------- Configuration ----------------
ULTRASONIC_FRONT = {
    "front_right":   (3, 2),
    "front_center":  (24, 25),
    "front_left":    (23, 18)
}

ULTRASONIC_REAR = {
    # "rear_left":    (17, 27),
    # "rear_center":  (23, 24),
    # "rear_right":   (25, 8)
}

ALL_SENSORS = {**ULTRASONIC_FRONT}   # Front only
# ALL_SENSORS = {**ULTRASONIC_FRONT, **ULTRASONIC_REAR}  # Uncomment for all 6

# Will store DistanceSensor objects
SENSOR_OBJECTS = {}

# ---------------- Setup gpiozero DistanceSensors ----------------
def setup_sensors():
    """
    Create gpiozero DistanceSensor objects for all sensors.
    (Uses trigger=<trig>, echo=<echo>)
    """
    global SENSOR_OBJECTS
    print("Initializing sensors...")

    SENSOR_OBJECTS = {}
    for name, (trig, echo) in ALL_SENSORS.items():
        try:
            sensor = DistanceSensor(
                trigger=trig,
                echo=echo,
                max_distance=4,      # meters
                queue_len=3          # smoothing
            )
            SENSOR_OBJECTS[name] = sensor
            print(f"✓ {name}: GPIO {trig} (trig), {echo} (echo)")
        except Exception as e:
            print(f"❌ Failed to initialize {name}: {e}")
            SENSOR_OBJECTS[name] = None

    print("✓ All sensors initialized\n")
    return True

# ---------------- Distance Reading ----------------
def read_distance_cm(name):
    """Return distance in cm or None on error."""
    sensor = SENSOR_OBJECTS.get(name)
    if sensor is None:
        return None
    try:
        dist_m = sensor.distance    # in meters
        if dist_m is None:
            return None
        return dist_m * 100.0
    except Exception:
        return None

# ---------------- Test Functions ----------------
def test_single_sensor(name, samples=5):
    """Test a single sensor with multiple readings."""
    print(f"\nTesting {name}")
    print("-" * 50)

    if name not in SENSOR_OBJECTS or SENSOR_OBJECTS[name] is None:
        print("❌ Sensor not available or failed to initialize")
        return False

    readings = []
    errors = 0

    for i in range(samples):
        dist = read_distance_cm(name)
        if dist is not None:
            readings.append(dist)
            status = "✓" if 2 <= dist <= 400 else "⚠️"
            print(f"  Sample {i+1}: {dist:6.1f} cm {status}")
        else:
            print(f"  Sample {i+1}: ERROR ❌")
            errors += 1
        time.sleep(0.1)

    if readings:
        avg = sum(readings)/len(readings)
        print(f"\nAverage: {avg:.1f} cm")
        print(f"Range:   {min(readings):.1f} – {max(readings):.1f} cm")
        print(f"Success: {len(readings)}/{samples}")

        if errors == 0:
            print("✓ Sensor working properly!")
        else:
            print(f"⚠️  {errors} errors detected")
    else:
        print("❌ No valid readings")

    return True

def test_all_sensors_once():
    print("\nReading all sensors...")
    print("-" * 70)
    print(f"{'Sensor':<15} {'Distance':<10} {'Status'}")
    print("-" * 70)

    for name in ALL_SENSORS:
        dist = read_distance_cm(name)
        if dist is None:
            print(f"{name:<15} {'ERROR':<10} ❌ FAIL")
        else:
            if 2 <= dist <= 400:
                print(f"{name:<15} {dist:6.1f} cm   ✓ OK")
            else:
                print(f"{name:<15} {dist:6.1f} cm   ⚠️  Out of range")

def continuous_monitoring():
    print("\nContinuous Monitoring (Ctrl+C to stop)\n")
    try:
        while True:
            readings = []
            for name in ALL_SENSORS:
                dist = read_distance_cm(name)
                readings.append(
                    f"{name}: {dist:.1f} cm" if dist else f"{name}: ERR"
                )
            print("\r" + " | ".join(readings), end="")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n✓ Stopped")

def visual_display():
    print("\nVisual Display Mode (Ctrl+C to stop)\n")
    try:
        while True:
            os.system('clear')
            print("ULTRASONIC SENSOR VISUAL DISPLAY\n")

            for name in ALL_SENSORS:
                dist = read_distance_cm(name)
                if dist is None:
                    print(f"{name:<15} ERROR")
                    continue

                if dist <= 100:
                    bar = "█" * int(dist/2)
                    print(f"{name:<15} [{dist:5.1f} cm] {bar}")
                else:
                    print(f"{name:<15} [{dist:5.1f} cm] ▓▓▓▓▓ (out)")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n✓ Stopped")

def obstacle_detection_test():
    print("\nObstacle Detection Test (Ctrl+C to stop)\n")
    OBSTACLE = 15

    try:
        while True:
            print("\n--- FRONT SENSORS ---")
            readings = {name: read_distance_cm(name) for name in ULTRASONIC_FRONT}

            for name, dist in readings.items():
                if dist is None:
                    print(f"{name}: ERROR")
                else:
                    print(f"{name}: {dist:.1f} cm")

            left = readings['front_left']
            center = readings['front_center']
            right = readings['front_right']

            print("\n💡 Decision:", end=" ")

            if center and center < OBSTACLE:
                print("Obstacle AHEAD → ", end="")
                print("LEFT" if left > right else "RIGHT")
            elif left and left < OBSTACLE:
                print("Obstacle LEFT → turn RIGHT")
            elif right and right < OBSTACLE:
                print("Obstacle RIGHT → turn LEFT")
            else:
                print("Clear path → FORWARD")

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n✓ Stopped")


def show_wiring_guide():
    print("\n" + "="*70)
    print("ULTRASONIC SENSOR WIRING GUIDE (gpiozero)")
    print("="*70)
    print("\nTrig → GPIO")
    print("Echo → GPIO (with voltage divider!)")
    print("VCC  → 5V")
    print("GND  → Ground\n")
    print(f"{'Sensor':<15} {'Trig':<10} {'Echo':<10}")
    print("-"*40)
    for name, (trig, echo) in ALL_SENSORS.items():
        print(f"{name:<15} {trig:<10} {echo:<10}")
    print("="*40)

# ---------------- Menu ----------------
def main_menu():
    while True:
        print("\n" + "="*60)
        print(" ULTRASONIC TEST TOOL (gpiozero)")
        print("="*60)
        print("1. Test Single Sensor")
        print("2. Test All Sensors")
        print("3. Continuous Monitoring")
        print("4. Visual Display")
        print("5. Obstacle Detection Test")
        print("6. Show Wiring Guide")
        print("7. Exit\n")

        choice = input("Select [1-7]: ").strip()

        if choice == "1":
            print("\nAvailable sensors:")
            for i, name in enumerate(ALL_SENSORS, start=1):
                print(f"  {i}. {name}")
            sel = input("Select sensor #: ")
            try:
                idx = int(sel) - 1
                name = list(ALL_SENSORS.keys())[idx]
                test_single_sensor(name, samples=10)
            except:
                print("Invalid selection!")

        elif choice == "2":
            test_all_sensors_once()
        elif choice == "3":
            continuous_monitoring()
        elif choice == "4":
            visual_display()
        elif choice == "5":
            obstacle_detection_test()
        elif choice == "6":
            show_wiring_guide()
        elif choice == "7":
            print("Goodbye!")
            break
        else:
            print("Invalid option")

# ---------------- Main ----------------
if __name__ == "__main__":
    print("="*60)
    print(" ULTRASONIC SENSOR TEST TOOL (gpiozero)")
    print("="*60)

    setup_sensors()
    main_menu()

    print("\n✓ Done")
