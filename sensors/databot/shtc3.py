# python
from machine import I2C, Pin
import time
import struct


class SHTC3:
    """Class to interface with the SHTC3 temperature & humidity sensor."""

    def __init__(self, i2c, address=0x70):
        self.i2c = i2c
        self.address = address
        self.wake()
        time.sleep(0.001)
        self._check_id()

    def _write_cmd(self, cmd):
        """Write a 16-bit command to the sensor."""
        self.i2c.writeto(self.address, bytes([cmd >> 8, cmd & 0xFF]))

    def _read_data(self, num_bytes):
        """Read specified number of bytes from the sensor."""
        return self.i2c.readfrom(self.address, num_bytes)

    def wake(self):
        """Wake up the sensor from sleep mode."""
        self._write_cmd(0x3517)

    def sleep(self):
        """Put the sensor in low power sleep mode."""
        self._write_cmd(0xB098)

    def _check_id(self):
        """Optional: verify sensor ID (for debugging)."""
        self._write_cmd(0xEFC8)
        time.sleep(0.001)
        data = self._read_data(2)
        chip_id = (data[0] << 8) | data[1]
        # print("SHTC3 ID:", hex(chip_id))
        return chip_id

    def read(self):
        """
        Read temperature (°C) and relative humidity (%RH).
        Returns a tuple: (temperature_c, humidity)
        """
        # Trigger measurement in normal mode (clock stretching disabled)
        self._write_cmd(0x7866)
        time.sleep(0.015)  # measurement time

        data = self._read_data(6)
        t_raw = (data[0] << 8) | data[1]
        h_raw = (data[3] << 8) | data[4]

        # Convert to human-readable values
        temperature = -45 + (175 * t_raw / 65535.0)
        humidity = 100 * h_raw / 65535.0

        return temperature, humidity


# ----- Example Usage -----
# Setup I2C for ESP32 (use your databot's SDA/SCL pins)
i2c = I2C(1, scl=Pin(22), sda=Pin(21))  # adjust pins if needed

shtc3 = SHTC3(i2c)

while True:
    temp, hum = shtc3.read()
    print("Temperature: {:.2f} °C, Humidity: {:.2f}%".format(temp, hum))
    time.sleep(2)

