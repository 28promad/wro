# main_databot.py
from databoot import Lights, Buzzer, AirQualitySensor, Humidity
import serial_databot
from machine import I2C, Pin
from imu_icm20948 import ICM20948
import time, ujson
from math import sqrt


# --- Hardware setup ---
lights = Lights(num_leds=3, pin=2)
buzzer = Buzzer(pin=32)
air = AirQualitySensor()
hum = Humidity()

# IMU (ICM-20948 at address 0x68)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
imu = ICM20948(i2c, addr=0x68)

# --- Threshold constants ---
CO2_LIMIT = 1000
VOC_LIMIT = 400
TEMP_LIMIT = 30
HUM_MIN, HUM_MAX = 30, 70

# --- Displacement variables ---
velocity = 0.0
displacement = 0.0
prev_time = time.ticks_ms()

# ----------------------  Helper functions  ----------------------
def wait_for_connection():
    """Wait for 'Start' command from the Raspberry Pi."""
    lights.set_all(255, 0, 0)
    print("Waiting for Raspberry Pi...")
    while True:
        msg = serial_databot.read_from_pi()
        if msg == "Start":
            for _ in range(3):
                lights.set_all(0, 255, 0)
                time.sleep(0.3)
                lights.off()
                time.sleep(0.3)
            lights.set_all(0, 255, 0)
            serial_databot.send_to_pi("ready")
            print("Connected to Pi!")
            break
        time.sleep(0.1)

def read_environment():
    co2 = air.read_co2() or 0
    voc = air.read_voc() or 0
    temp, humi = hum.read()
    return co2, voc, temp or 0, humi or 0

def read_imu():
    ax, ay, az = imu.accel()
    gx, gy, gz = imu.gyro()
    return ax, ay, az, gx, gy, gz

def update_displacement(ax):
    """Estimate displacement (m) using integration with drift correction."""
    global velocity, displacement, prev_time
    now = time.ticks_ms()
    dt = time.ticks_diff(now, prev_time) / 1000.0
    prev_time = now

    if abs(ax) < 0.05:  # ignore tiny jitters
        ax = 0

    velocity += ax * dt
    velocity *= 0.98       # damping to reduce drift
    displacement += velocity * dt
    return displacement

def status_feedback(co2, voc, temp, hum):
    """Update LEDs and buzzer according to environmental safety."""
    if co2 > CO2_LIMIT or voc > VOC_LIMIT:
        lights.set_one(0, 255, 0, 0)
        buzzer.beep(800, 100)
    else:
        lights.set_one(0, 0, 255, 0)
    if temp > TEMP_LIMIT:
        lights.set_one(1, 255, 0, 0)
    else:
        lights.set_one(1, 0, 255, 0)
    if hum < HUM_MIN or hum > HUM_MAX:
        lights.set_one(2, 255, 0, 0)
    else:
        lights.set_one(2, 0, 255, 0)

def send_data():
    """Gather all sensor readings and send as JSON string."""
    co2, voc, temp, hum = read_environment()
    ax, ay, az, gx, gy, gz = read_imu()
    disp = update_displacement(ax)

    data = {
        "co2": co2, "voc": voc, "temp": temp, "hum": hum,
        "ax": ax, "ay": ay, "az": az,
        "gx": gx, "gy": gy, "gz": gz,
        "disp": disp
    }

    serial_databot.send_to_pi(ujson.dumps(data))
    status_feedback(co2, voc, temp, hum)

# ----------------------  Main loop  ----------------------
def main():
    wait_for_connection()
    last_send = time.ticks_ms()

    while True:
        msg = serial_databot.read_from_pi()
        if msg and msg.lower() == "stop":
            lights.off()
            break

        if time.ticks_diff(time.ticks_ms(), last_send) > 1000:
            send_data()
            last_send = time.ticks_ms()
        time.sleep(0.05)

if __name__ == "__main__":
    main()
