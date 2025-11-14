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
# hum = Humidity()

# IMU (ICM-20948 at address 0x68)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
imu = ICM20948(i2c, addr=0x68)

# --- Threshold constants ---
CO2_LIMIT = 1000
VOC_LIMIT = 400
TEMP_LIMIT = 30
HUM_MIN, HUM_MAX = 30, 70

# DISPLACEMENT VARIABLES
velocity = 0.0
displacement = 0.0


def read_environment():
    co2 = air.read_co2() or 0
    voc = air.read_voc() or 0
    # temp, humi = hum.read()
    # return co2, voc, temp or 0, humi or 0
    
    return co2, voc




while True:
    # co2, voc, temp, hum = read_environment()
    co2, voc = read_environment()
    print(f"{co2, voc}", flush=True)
    # print(f"{co2, voc, temp, hum}", "\n")
    print("Hi, from databot", "\n")
    time.sleep(1)