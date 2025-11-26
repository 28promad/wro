#!/usr/bin/env python3
# test_ultrasonic_pigpio.py
# Fully refactored ultrasonic sensor test tool using pigpio
# Works on Raspberry Pi 4B and Raspberry Pi 5

import time
import sys
import os
import pigpio

# ============================================================
#          HARDWARE-TIMED HC-SR04 DRIVER USING pigpio
# ============================================================

class HCSR04:
    """
    HC-SR04 ultrasonic distance sensor using pigpio hardware timing.
    Reliable on Pi 4 + Pi 5.
    """
    def __init__(self, trigger_pin, echo_pin, timeout=0.04):
        self.trigger = trigger_pin
        self.echo = echo_pin
        self.timeout = timeout

        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("❌ pigpio daemon not running! Start with: sudo systemctl start pigpiod")

        # Setup pins
        self.pi.set_mode(self.trigger, pigpio.OUT)
        self.pi.set_mode(self.echo, pigpio.IN)
        self.pi.write(self.trigger, 0)

        self.high_tick = None
        self.echo_time = None

        # Setup callback for echo rising/falling edges
        self.cb = self.pi.callback(self.echo, pigpio.EITHER_EDGE, self._callback)

    def _callback(self, gpio, level, tick):
        if level == 1:  # rising edge
            self.high_tick = tick
        elif level == 0 and self.high_tick is not None:  # falling
            self.echo_time = pigpio.tickDiff(self.high_tick, tick)
            self.high_tick = None

    def read(self):
        """
        Returns distance in centimeters, or None on timeout.
        """
        self.echo_time = None

        # 10 microsecond trigger pulse
        self.pi.gpio_trigger(self.trigger, 10)

        start = time.time()
        while self.echo_time is None:
            if (time.time() - start) > self.timeout:
                return None
            time.sleep(0.00001)

        # Convert time (microseconds) to distance in cm
        distance_cm = (self.echo_time / 1_000_000) * 17150
        return distance_cm

    def cleanup(self):
        self.cb.cancel()
        self.pi.stop()


# ============================================================
#                    SENSOR CONFIGURATION
# ============================================================

# Front sensors
ULTRASONIC_FRONT = {
    "front_right":  (6, 5),
    "front_center": (24, 25),
    "front_left":   (23, 18)
}

# Rear sensors (disabled)
ULTRASONIC_REAR = {}

ALL_SENSORS = {**ULTRASONIC_FRONT}

SENSOR_OBJS = {}  # Populated in setup_sensors()


# ============================================================
#                   INITIALIZATION
# ============================================================

def setup_sensors():
    """Initialize all HC-SR04 objects."""
    print("\nInitializing sensors with pigpio...\n")

    for name, (trig, echo) in ALL_SENSORS.items():
        try:
            SENSOR_OBJS[name] = HCSR04(trig, echo)
            print(f"✓ {name} initialized (Trig={trig}, Echo={echo})")
        except Exception as e:
            print(f"❌ Failed to initialize {name}: {e}")
            SENSOR_OBJS[name] = None

    print("")
    return True


# ============================================================
#                   MEASUREMENT FUNCTIONS
# ============================================================

def measure(name):
    """Take one measurement from a specific sensor."""
    sensor = SENSOR_OBJS.get(name)
    if sensor is None:
        return None
    return sensor.read()


def test_single_sensor(name, trig, echo, samples=5):
    print(f"\nTesting {name} (Trig={trig}, Echo={echo})")
    print("-" * 50)

    readings = []
    errors = 0

    for i in range(samples):
        dist = measure(name)

        if dist is not None:
            readings.append(dist)
            status = "✓" if 2 <= dist <= 400 else "⚠️"
            print(f"  Sample {i+1}: {dist:6.1f} cm {status}")
        else:
            errors += 1
            print(f"  Sample {i+1}: TIMEOUT ❌")

        time.sleep(0.1)

    if readings:
        avg = sum(readings) / len(readings)
        print(f"\n  Average: {avg:.1f} cm")
        print(f"  Range:   {min(readings):.1f} - {max(readings):.1f} cm")
        print(f"  Success: {len(readings)}/{samples}")
        print("  ✓ Sensor working properly!" if errors == 0 else f"  ⚠️ {errors} errors detected")
    else:
        print("  ❌ All measurements failed!")

    return bool(readings)


def test_all_sensors_once():
    print("\nReading all sensors...")
    print("-" * 70)
    print(f"{'Sensor':<15} {'Position':<12} {'Distance':<10} {'Status'}")
    print("-" * 70)

    for name, (trig, echo) in ALL_SENSORS.items():
        dist = measure(name)
        pos = name.replace("_", " ").title()

        if dist is None:
            print(f"{name:<15} {pos:<12} {'TIMEOUT':<10} ❌ Error")
        else:
            status = "✓ OK" if 2 <= dist <= 400 else "⚠️ Out of range"
            print(f"{name:<15} {pos:<12} {dist:6.1f}cm   {status}")


def continuous_monitoring():
    print("\nContinuous Monitoring Mode (Ctrl+C to stop)\n")

    try:
        while True:
            line = []
            for name in ALL_SENSORS.keys():
                d = measure(name)
                if d is None:
                    line.append(f"{name}: ERR")
                else:
                    line.append(f"{name}: {d:5.1f}cm")
            print("\r" + " | ".join(line), end="")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n\n✓ Monitoring stopped")


def visual_display():
    print("\nVisual Display (Ctrl+C to stop)\n")

    try:
        while True:
            os.system("clear")
            print("╔══════════════════════════════════════════════╗")
            print("║          ULTRASONIC SENSOR DISPLAY          ║")
            print("╚══════════════════════════════════════════════╝\n")

            for name in ALL_SENSORS.keys():
                dist = measure(name)
                if dist is None:
                    print(f"{name:15}  ERROR")
                else:
                    bar = "█" * int(min(dist / 2, 50))
                    print(f"{name:15} [{dist:5.1f}cm] {bar}")

            print("\nPress Ctrl+C to exit")
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n✓ Display stopped")


def obstacle_detection_test():
    print("\nObstacle Detection Test (Ctrl+C to stop)\n")
    OBST = 15.0

    try:
        while True:
            time.sleep(0.5)
            readings = {name: measure(name) or float("inf") for name in ULTRASONIC_FRONT}

            left = readings["front_left"]
            center = readings["front_center"]
            right = readings["front_right"]

            print("\n--- FRONT SENSORS ---")
            for n, v in readings.items():
                print(f"{n}: {v:.1f} cm")

            print("\nDecision:", end=" ")

            if center < OBST:
                print("Turn LEFT" if left > right else "Turn RIGHT")
            elif left < OBST:
                print("Adjust RIGHT")
            elif right < OBST:
                print("Adjust LEFT")
            else:
                print("FORWARD")

    except KeyboardInterrupt:
        print("\n✓ Test stopped")


def show_wiring_guide():
    print("\n" + "=" * 60)
    print("                    WIRING GUIDE")
    print("=" * 60)
    print("\nEach HC-SR04 needs VCC, GND, Trig, Echo")
    print("Echo MUST use a 1kΩ + 2kΩ voltage divider!\n")

    print(f"{'Sensor':<15} {'Trig Pin':<10} {'Echo Pin':<10}")
    print("-" * 60)

    for name, (trig, echo) in ALL_SENSORS.items():
        print(f"{name:<15} {trig:<10} {echo:<10}")

    print("=" * 60)


# ============================================================
#                         MAIN MENU
# ============================================================

def main_menu():
    while True:
        print("\n" + "=" * 70)
        print("           🔍 ULTRASONIC SENSOR TEST TOOL (pigpio)")
        print("=" * 70)
        print("\n1. Test Single Sensor")
        print("2. Test All Sensors")
        print("3. Continuous Monitoring")
        print("4. Visual Display")
        print("5. Obstacle Detection Test")
        print("6. Show Wiring Guide")
        print("7. Exit\n")

        choice = input("Select option [1-7]: ").strip()

        if choice == "1":
            print("\nAvailable sensors:")
            for i, name in enumerate(ALL_SENSORS.keys(), 1):
                print(f" {i}. {name}")
            sel = input("\nSelect sensor: ")
            try:
                name = list(ALL_SENSORS.keys())[int(sel)-1]
                trig, echo = ALL_SENSORS[name]
                test_single_sensor(name, trig, echo, samples=10)
            except:
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
            show_wiring_guide()

        elif choice == "7":
            break

        else:
            print("❌ Invalid option")


# ============================================================
#                     PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("           🔍 ULTRASONIC SENSOR TEST TOOL (pigpio)")
    print("           Compatible with Pi 4B and Pi 5")
    print("=" * 70)

    try:
        setup_sensors()
        main_menu()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    finally:
        for s in SENSOR_OBJS.values():
            if s:
                s.cleanup()
        print("✓ pigpio cleanup complete")
