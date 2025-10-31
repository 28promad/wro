# python
# MicroPython script for ESP32 + SGP30 Air Quality Sensor
# Reads CO2eq (ppm) and TVOC (ppb) values and prints them every 2 seconds

from machine import I2C, Pin
from time import sleep_ms, sleep

class SGP30:
    def __init__(self, i2c, address=0x58):
        self.i2c = i2c
        self.address = address
        self._init_air_quality()

    def _send_command(self, cmd):
        self.i2c.writeto(self.address, bytes(cmd))
        sleep_ms(10)

    def _init_air_quality(self):
        # Initialize air quality measurement
        self._send_command([0x20, 0x03])
        sleep_ms(10)

    def measure_air_quality(self):
        # Trigger measurement
        self._send_command([0x20, 0x08])
        sleep_ms(12)
        data = self.i2c.readfrom(self.address, 6)
        co2eq = (data[0] << 8) | data[1]
        tvoc = (data[3] << 8) | data[4]
        return co2eq, tvoc


# --- MAIN PROGRAM ---
def main():
    # Initialize I2C on standard ESP32 pins (SDA=21, SCL=22)
    i2c = I2C(0, scl=Pin(22), sda=Pin(21))

    # Create sensor instance
    sensor = SGP30(i2c)
    print("SGP30 Air Quality Sensor initialized.")
    print("Waiting for readings to stabilize...\n")

    # Continuous measurement loop
    while True:
        co2, tvoc = sensor.measure_air_quality()
        print("\tCO₂eq: {:>5} ppm | TVOC: {:>5} ppb".format(co2, tvoc))
        sleep(2)


# Run main
if __name__ == "__main__":
    main()

