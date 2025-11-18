# test_imu.py
from machine import I2C, Pin
from imu_icm20948 import ICM20948
import time

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
imu = ICM20948(i2c)

while True:
    ax, ay, az = imu.accel()
    gx, gy, gz = imu.gyro()
    print("Accel (m/s²):", ax, ay, az)
    print("Gyro (°/s):", gx, gy, gz)
    time.sleep(0.5)
