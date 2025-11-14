# imu_icm20948.py
# Minimal ICM-20948 I2C driver for Databot
from machine import I2C
import struct, time

class ICM20948:
    """Basic ICM-20948 driver (accel + gyro)."""
    def __init__(self, i2c, addr=0x69):
        self.i2c = i2c
        self.addr = addr
        # Wake up device (exit sleep)
        self._write_reg(0x06, 0x01)  # PWR_MGMT_1
        time.sleep(0.05)
        print("ICM20948 initialized at address 0x69")

    def _write_reg(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val]))

    def _read_bytes(self, reg, n):
        return self.i2c.readfrom_mem(self.addr, reg, n)

    def _read_word(self, reg):
        data = self._read_bytes(reg, 2)
        return struct.unpack(">h", data)[0]

    def accel(self):
        """Return acceleration (m/s²) as (ax, ay, az)."""
        # ACCEL_XOUT_H starts at 0x2D in ICM-20948 user bank 2
        data = self._read_bytes(0x2D, 6)
        ax, ay, az = struct.unpack(">hhh", data)
        scale = 16 * 9.80665 / 32768.0  # ±16g full scale
        return ax * scale, ay * scale, az * scale

    def gyro(self):
        """Return angular velocity (°/s) as (gx, gy, gz)."""
        # GYRO_XOUT_H starts at 0x33
        data = self._read_bytes(0x33, 6)
        gx, gy, gz = struct.unpack(">hhh", data)
        scale = 2000 / 32768.0  # ±2000°/s
        return gx * scale, gy * scale, gz * scale

    def temperature(self):
        """Return temperature in °C."""
        raw = self._read_word(0x39)
        return (raw / 333.87) + 21.0
