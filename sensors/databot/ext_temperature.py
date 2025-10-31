# python
from machine import Pin
import onewire, ds18x20, time

class ExternalTempSensor:
    """Class to read temperature from DS18B20 external probes."""

    def __init__(self, pin1=23, pin2=4):
        """
        Initialize two DS18B20 sensors connected to pins 23 and 4.
        If only one probe is connected, it will still work.
        """
        self.sensors = []
        for pin in (pin1, pin2):
            try:
                ow = onewire.OneWire(Pin(pin))
                ds = ds18x20.DS18X20(ow)
                roms = ds.scan()
                if roms:
                    self.sensors.append((ds, roms[0]))  # use the first sensor found
            except Exception as e:
                print(f"Error initializing sensor on pin {pin}: {e}")

    def read_temperatures(self):
        """
        Reads all available DS18B20 sensors.
        Returns a list of (pin, temperature °C) tuples.
        """
        results = []
        for index, (ds, rom) in enumerate(self.sensors):
            ds.convert_temp()
            time.sleep_ms(750)  # Wait for conversion
            temp = ds.read_temp(rom)
            results.append((index, temp))
        return results

# ----- Example Usage -----
temps = ExternalTempSensor(pin1=23, pin2=4)

while True:
    readings = temps.read_temperatures()
    for i, t in readings:
        print("Probe", i + 1, "Temperature: {:.2f} °C".format(t))
    time.sleep(2)

