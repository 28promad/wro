# main_databot.py
from databoot import Lights, Buzzer, AirQualitySensor, Humidity
import serial_databot
from machine import I2C, Pin
from imu import MPU6050  # assuming the IMU class exists or add it
import time, ujson

# --- Hardware setup ---
lights = Lights(num_leds=3, pin=2)
buzzer = Buzzer(pin=32)
air = AirQualitySensor()
hum = Humidity()

# Example IMU setup (I2C pins depend on Databot layout)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
imu = MPU6050(i2c)

# --- Constants ---
CO2_LIMIT = 1000
VOC_LIMIT = 400
TEMP_LIMIT = 30
HUM_MIN, HUM_MAX = 30, 70

def wait_for_connection():
    """Wait until Pi sends start signal."""
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
    temp = temp or 0
    humi = humi or 0
    return co2, voc, temp, humi

def read_imu():
    """Return acceleration-based displacement estimate (basic integration)."""
    accel = imu.accel  # dict {'x':.., 'y':.., 'z':..}
    gyro = imu.gyro
    return accel['x'], accel['y'], accel['z'], gyro['x'], gyro['y'], gyro['z']

def status_feedback(co2, voc, temp, hum):
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
    """Send combined environment + IMU data."""
    co2, voc, temp, hum = read_environment()
    ax, ay, az, gx, gy, gz = read_imu()
    data = {
        "co2": co2, "voc": voc, "temp": temp, "hum": hum,
        "ax": ax, "ay": ay, "az": az, "gx": gx, "gy": gy, "gz": gz
    }
    serial_databot.send_to_pi(ujson.dumps(data))
    status_feedback(co2, voc, temp, hum)

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
