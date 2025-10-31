# main_databot.py
from databoot import Lights, Buzzer, AirQualitySensor, Humidity
from comms import serial_databot
import time

# --- Initialize components ---
lights = Lights(num_leds=3, pin=2)
buzzer = Buzzer(pin=32)
air = AirQualitySensor()
hum = Humidity()

# --- Thresholds ---
CO2_LIMIT = 1000
VOC_LIMIT = 400
TEMP_LIMIT = 30
HUM_MIN, HUM_MAX = 30, 70

def startup_sequence():
    """Startup LEDs and wait for connection."""
    lights.set_all(255, 0, 0)
    print("Waiting for connection from Raspberry Pi...")

    while True:
        msg = serial_databot.read_from_pi()
        if msg == "Start":
            print("Connected! Blinking green...")
            for _ in range(3):
                lights.set_all(0, 255, 0)
                time.sleep(0.3)
                lights.off()
                time.sleep(0.3)
            lights.set_all(0, 255, 0)
            serial_databot.send_to_pi("ready")
            break
        time.sleep(0.1)

def set_led_status(co2, voc, temp, humi):
    """Set LED colors based on threshold checks."""
    # Air quality LED
    if co2 is None or voc is None:
        lights.set_one(0, 128, 128, 0)  # yellow (unknown)
    elif co2 > CO2_LIMIT or voc > VOC_LIMIT:
        lights.set_one(0, 255, 0, 0)    # red
    else:
        lights.set_one(0, 0, 255, 0)    # green

    # Temperature LED
    if temp is None:
        lights.set_one(1, 128, 128, 0)
    elif temp > TEMP_LIMIT:
        lights.set_one(1, 255, 0, 0)
    else:
        lights.set_one(1, 0, 255, 0)

    # Humidity LED
    if humi is None:
        lights.set_one(2, 128, 128, 0)
    elif humi < HUM_MIN or humi > HUM_MAX:
        lights.set_one(2, 255, 0, 0)
    else:
        lights.set_one(2, 0, 255, 0)

def check_and_warn(co2, voc, temp, humi):
    """Beep when any value is unsafe."""
    if (co2 and co2 > CO2_LIMIT) or (voc and voc > VOC_LIMIT) or \
       (temp and temp > TEMP_LIMIT) or (humi and (humi < HUM_MIN or humi > HUM_MAX)):
        buzzer.beep(1000, 150)

def send_readings(co2, voc, temp, humi):
    """Format and send readings to the Pi."""
    data_str = f"[co2:{co2},tvoc:{voc},temp:{temp:.2f},hum:{humi:.2f}]"
    serial_databot.send_to_pi(data_str)
    print("Sent →", data_str)

def main_loop():
    print("Monitoring environment...")
    last_send_time = time.ticks_ms()

    while True:
        # --- Check for incoming Pi commands ---
        msg = serial_databot.read_from_pi()
        if msg:
            if msg.lower() == "ping":
                serial_databot.send_to_pi("pong")
            elif msg.lower() == "stop":
                lights.off()
                serial_databot.send_to_pi("stopped")
                break

        # --- Read sensors ---
        co2 = air.read_co2()
        voc = air.read_voc()
        temp, humi = hum.read()

        # --- Update LEDs and beep if needed ---
        set_led_status(co2, voc, temp, humi)
        check_and_warn(co2, voc, temp, humi)

        # --- Send data every 2 seconds ---
        if time.ticks_diff(time.ticks_ms(), last_send_time) > 2000:
            send_readings(co2, voc, temp, humi)
            last_send_time = time.ticks_ms()

        # --- Short delay to avoid hogging CPU ---
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        startup_sequence()
        main_loop()
    except KeyboardInterrupt:
        lights.off()
        print("Stopped by user.")
