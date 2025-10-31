# databot.py
# All-in-one helper library for Databot Board
# For middle school STEM activities
from machine import Pin, PWM, I2C, ADC
import neopixel, onewire, ds18x20, time, network
import ujson, os, time, math, ustruct
from umqtt.simple import MQTTClient
from time import sleep

from apds9960.const import *
from apds9960 import uAPDS9960 as APDS9960

from sgp30 import Adafruit_SGP30   # Adafruit driver


#----------------------------------------------
# 🧭 Humidity and Temperature Sensor (SHTC3)
# ---------------------------------------------
class Humidity:
    """
    Wrapper for the SHTC3 humidity and temperature sensor.
    Provides:
        - Temperature in °C
        - Relative Humidity in %
        - Automatic CRC check for data integrity
        - Power saving (auto sleep after each measurement)
    """

    SHTC3_I2C_ADDR = 0x70
    CMD_MEASURE_NORMAL = b'\x78\x66'
    CMD_SLEEP = b'\xB0\x98'
    CMD_WAKEUP = b'\x35\x17'

    def __init__(self, sda_pin=21, scl_pin=22, i2c_id=0):
        self.i2c = I2C(i2c_id, sda=Pin(sda_pin), scl=Pin(scl_pin))
        print("SHTC3 Humidity sensor initialized on SDA={}, SCL={}".format(sda_pin, scl_pin))

    # --- Internal CRC8 check based on SHTC3 datasheet ---
    def _crc8(self, data):
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                crc = ((crc << 1) ^ 0x31) if (crc & 0x80) else (crc << 1)
            crc &= 0xFF
        return crc

    def _read_sensor(self):
        """Low-level read from the SHTC3 sensor."""
        try:
            # Wake up sensor
            self.i2c.writeto(self.SHTC3_I2C_ADDR, self.CMD_WAKEUP)
            time.sleep_ms(1)

            # Send measure command (normal mode)
            self.i2c.writeto(self.SHTC3_I2C_ADDR, self.CMD_MEASURE_NORMAL)
            time.sleep_ms(15)  # Wait for measurement

            # Read 6 bytes: temp(2) + CRC(1) + hum(2) + CRC(1)
            data = self.i2c.readfrom(self.SHTC3_I2C_ADDR, 6)

            # Sleep to save power
            self.i2c.writeto(self.SHTC3_I2C_ADDR, self.CMD_SLEEP)

            temp_raw, temp_crc, hum_raw, hum_crc = ustruct.unpack('>HBHB', data)

            # Validate CRC
            if self._crc8(data[0:2]) != temp_crc:
                raise RuntimeError("Temperature CRC check failed")
            if self._crc8(data[3:5]) != hum_crc:
                raise RuntimeError("Humidity CRC check failed")

            # Convert to human-readable values
            temperature = 175 * (temp_raw / 65536) - 45
            humidity = 100 * (hum_raw / 65536)
            return temperature, humidity

        except Exception as e:
            print("SHTC3 read error:", e)
            return None, None

    def read(self):
        """Public method for classroom use: returns (temperature °C, humidity %)."""
        return self._read_sensor()

    def read_hum(self):
        temp, hum = self._read_sensor()
        return hum

    def describe(self, temperature, humidity):
        """Return a qualitative description of comfort level."""
        if temperature is None or humidity is None:
            return "Sensor not responding ❌"
        if 20 <= temperature <= 26 and 30 <= humidity <= 60:
            return "Comfortable ✅"
        elif humidity < 30:
            return "Dry 😐"
        elif humidity > 70:
            return "Humid 🌧️"
        else:
            return "Moderate ⚠️"

# -----------------------
# Air Quality Sensor (SGP30)
# -----------------------

class AirQualitySensor:
    """
    Student-friendly wrapper for the SGP30 gas sensor.
    
    Features:
    - Read eCO2 (ppm) and TVOC (ppb)
    - Burn-in period on first init for stable values
    - Optional baseline management
    - Optional humidity compensation
    - Color-coded air quality levels for easy understanding
    """
    def __init__(self, scl_pin=22, sda_pin=21, i2c_id=0, warm_up=15):
        self.i2c = I2C(i2c_id, scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.sensor = Adafruit_SGP30(self.i2c)

        # Initialize internal IAQ algorithm
        self.sensor.iaq_init()

        if warm_up < 15:
            raise ValueError("Baseline initialization must be at least 15 seconds.")
        else:
            print(f"SGP30 sensor initialized. Waiting for ", warm_up, " seconds for baseline...")
            for _ in range(warm_up):
                self.sensor.iaq_measure()
                time.sleep(1)

    def read_co2(self):
        """Read CO2 (ppm) and VOC (ppb)."""
        try:
            values = self.sensor.iaq_measure()
            co2 = values[0]
            if co2 is not None:
                return co2
        except Exception as e:
            print("SGP30 read error:", e)
        return None

    def read_voc(self):
        """Read CO2 (ppm) and VOC (ppb)."""
        try:
            values = self.sensor.iaq_measure()
            voc = values[1]
            if voc is not None:
                return voc
        except Exception as e:
            print("SGP30 read error:", e)
        return None

    def get_baseline(self):
        """Get current baseline values (CO2, VOC)."""
        try:
            return self.sensor.get_iaq_baseline()
        except Exception as e:
            print("Error getting baseline:", e)
            return None, None

    def set_baseline(self, baseline_CO2, baseline_VOC):
        """Restore baseline for long-term accuracy."""
        try:
            self.sensor.set_iaq_baseline(baseline_CO2, baseline_VOC)
        except Exception as e:
            print("Error setting baseline:", e)

    def set_humidity(self, absolute_humidity):
        """
        Optional: provide absolute humidity in g/m^3.
        Helps improve accuracy in humid environments.
        """
        try:
            self.sensor.set_humidity(absolute_humidity)
        except Exception as e:
            print("Error setting humidity:", e)

    def air_quality_level(self, CO2, VOC):
        """
        Convert readings into human-readable status.
        Returns a string label with emoji.
        """
        if CO2 is None or VOC is None:
            return "Unknown ❓"

        if CO2 < 600 and VOC < 200:
            return "Excellent ✅"
        elif CO2 < 1000 and VOC < 400:
            return "Good 🙂"
        elif CO2 < 2000 or VOC < 1000:
            return "Moderate 😐"
        else:
            return "Poor ⚠️"

# -----------------------
# LED Ring (WS2812C-2020)
# -----------------------

class Lights:
    def __init__(self, num_leds=8, pin=2, brightness=1.0):
        self.num_leds = num_leds
        self.np = neopixel.NeoPixel(Pin(pin), num_leds)
        self.brightness = max(0, min(brightness, 1.0))  # clamp 0.0-1.0

    def _apply_brightness(self, r, g, b):
        """Scale RGB values by brightness (0.0–1.0)."""
        return (
            int(r * self.brightness),
            int(g * self.brightness),
            int(b * self.brightness)
        )

    def set_all(self, r, g, b):
        r, g, b = self._apply_brightness(r, g, b)
        for i in range(self.num_leds):
            self.np[i] = (r, g, b)
        self.np.write()

    def set_one(self, index, r, g, b):
        if 0 <= index < self.num_leds:
            r, g, b = self._apply_brightness(r, g, b)
            self.np[index] = (r, g, b)
            self.np.write()

    def rainbow(self):
        colors = [(255, 0, 0), (255, 127, 0), (255, 255, 0),
                  (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)]
        for i in range(self.num_leds):
            r, g, b = self._apply_brightness(*colors[i % len(colors)])
            self.np[i] = (r, g, b)
        self.np.write()

    def off(self):
        self.set_all(0, 0, 0)

    def set_brightness(self, brightness):
        """Set brightness 0.0–1.0."""
        self.brightness = max(0, min(brightness, 1.0))

# -----------------------
# Temperature Sensors (DS18B20) for fixed pins
# -----------------------

class Temperature:
    def __init__(self):
        # Fixed pins: Probe 1 = 23, Probe 2 = 4
        self.ds1 = ds18x20.DS18X20(onewire.OneWire(Pin(4)))
        self.ds2 = ds18x20.DS18X20(onewire.OneWire(Pin(23)))
        self.roms1 = self.ds1.scan()
        self.roms2 = self.ds2.scan()
        if not self.roms1:
            print("No sensor found on probe 1")
        if not self.roms2:
            print("No sensor found on probe 2")

    def probe1(self):
        """Read temperature from probe 1 in °C."""
        if not self.roms1:
            return None
        self.ds1.convert_temp()
        time.sleep_ms(750)
        return self.ds1.read_temp(self.roms1[0])

    def probe2(self):
        """Read temperature from probe 2 in °C."""
        if not self.roms2:
            return None
        self.ds2.convert_temp()
        time.sleep_ms(750)
        return self.ds2.read_temp(self.roms2[0])

    def average(self, probe=1, readings=5):
        """
        Take multiple readings and return the average temperature.
        
        probe: 1 or 2 (which sensor to read)
        readings: how many times to read the sensor
        """
        total = 0
        count = 0
        read_func = self.probe1 if probe == 1 else self.probe2
        for _ in range(readings):
            val = read_func()
            if val is not None:
                total += val
                count += 1
            time.sleep_ms(200)  # short delay between readings
        return total / count if count > 0 else None

    # Kid-friendly shortcuts
    def avg1(self, readings=5):
        """Average temperature from probe 1."""
        return self.average(probe=1, readings=readings)

    def avg2(self, readings=5):
        """Average temperature from probe 2."""
        return self.average(probe=2, readings=readings)

# -----------------------
# Buzzer (SMT-0540-T-2-R)
# -----------------------

class Buzzer:
    # Standard note frequencies (in Hz)
    NOTES = {
        # Piano keys A0–C8
        "A0": 27, "A#0": 29, "B0": 31,
        "C1": 33, "C#1": 35, "D1": 37, "D#1": 39, "E1": 41, "F1": 44, "F#1": 46, "G1": 49, "G#1": 52, "A1": 55, "A#1": 58, "B1": 62,
        "C2": 65, "C#2": 69, "D2": 73, "D#2": 78, "E2": 82, "F2": 87, "F#2": 93, "G2": 98, "G#2": 104, "A2": 110, "A#2": 117, "B2": 123,
        "C3": 131, "C#3": 139, "D3": 147, "D#3": 156, "E3": 165, "F3": 175, "F#3": 185, "G3": 196, "G#3": 208, "A3": 220, "A#3": 233, "B3": 247,
        "C4": 261, "C#4": 277, "D4": 293, "D#4": 311, "E4": 329, "F4": 349, "F#4": 370, "G4": 392, "G#4": 415, "A4": 440, "A#4": 466, "B4": 493,
        "C5": 523, "C#5": 554, "D5": 587, "D#5": 622, "E5": 659, "F5": 698, "F#5": 740, "G5": 784, "G#5": 831, "A5": 880, "A#5": 932, "B5": 987,
        "C6": 1046, "C#6": 1108, "D6": 1174, "D#6": 1244, "E6": 1318, "F6": 1396, "F#6": 1480, "G6": 1568, "G#6": 1661, "A6": 1760, "A#6": 1865, "B6": 1976,
        "C7": 2093, "C#7": 2217, "D7": 2349, "D#7": 2489, "E7": 2637, "F7": 2793, "F#7": 2960, "G7": 3136, "G#7": 3322, "A7": 3520, "A#7": 3729, "B7": 3951,
        "C8": 4186
    }

    def __init__(self, pin=32):
        self.pin = pin
        self.buzzer = PWM(Pin(self.pin))
        self.buzzer.deinit()

    def beep(self, freq=1000, duration=200):
        """Beep at a frequency (Hz) for a duration (ms)."""
        self.buzzer = PWM(Pin(self.pin), freq=freq, duty=512)
        time.sleep_ms(duration)
        self.buzzer.deinit()

    def play_tone(self, note_or_freq, duration=200, error_beep=True):
        """
        Play a tone given a note name or frequency.
        
        note_or_freq: string like "C4", "A4" or numeric frequency in Hz
        duration: milliseconds
        error_beep: if True, play a low beep when note is unknown
        """
        if isinstance(note_or_freq, str):
            freq = self.NOTES.get(note_or_freq.upper())
            if freq is None:
                print(f"Warning: Unknown note '{note_or_freq}'")
                if error_beep:
                    freq = 100  # low error beep
                else:
                    return  # do nothing
        else:
            freq = note_or_freq

        self.beep(freq, duration)

# -----------------------
# APDS9960 
# -----------------------

class APDS9960Sensor:
    def __init__(self, scl=22, sda=21, address=0x39):
        """
        scl, sda: ESP32 I2C pins (default GPIO22=SCL, GPIO21=SDA)
        """
        self.i2c = I2C(0, scl=Pin(scl), sda=Pin(sda))
        self.sensor = APDS9960(self.i2c, address)

        # Enable the built-in features
        self.sensor.enableProximitySensor(interrupts=False)
        self.sensor.enableGestureSensor(interrupts=False)
        self.sensor.enableLightSensor(interrupts=False)
        time.sleep(0.25)  # settle time

    # --- Ambient light ---
    def light(self):
        """Return raw ambient light (clear channel)"""
        if self.sensor.isLightAvailable():
            return self.sensor.readAmbientLight()
        return self.sensor.readAmbientLight()

    def lux(self):
        """Return ambient light in lux (approximation)"""
        if self.sensor.isLightAvailable():
            return round(self.sensor.ambient_to_lux(), 2)
        return self.sensor.ambient_to_lux()

    def get_rgb(self):
        # Try to read all values and normalize
        try:
            r = self.sensor.readRedLight()
            g = self.sensor.readGreenLight()
            b = self.sensor.readBlueLight()
            c = self.sensor.readAmbientLight()
            
            # Only normalize if ambient light reading is valid (non-zero)
            if c > 0:
                return self.sensor.normalize_rgb(r, g, b, c)
            else:
                # Fallback if ambient light is zero
                return (r, g, b)
        except Exception as e:
            # Fallback if sensor fails
            print("Sensor read error:", e)
            return (0, 0, 0)
        
    # --- Color sensor ---
    def rgb(self):
        """Return normalized RGB values (0–255)"""
        if self.sensor.isLightAvailable():
            r = self.sensor.readRedLight()
            g = self.sensor.readGreenLight()
            b = self.sensor.readBlueLight()
            c = self.sensor.readAmbientLight()
            return self.sensor.normalize_rgb(r, g, b, c)
        return (self.sensor.readRedLight(), self.sensor.readGreenLight(), self.sensor.readBlueLight() )

    # --- Proximity ---
    def proximity(self):
        """Return proximity value (0–255)"""
        return self.sensor.readProximity()

    # --- Gesture ---
    def gesture(self):
        """Return gesture as text label, or None"""
        if self.sensor.isGestureAvailable():
            g = self.sensor.readGesture()
            gestures = {
                0x01: "UP",
                0x02: "DOWN",
                0x03: "LEFT",
                0x04: "RIGHT",
                0x05: "NEAR",
                0x06: "FAR",
            }
            return gestures.get(g, "UNKNOWN")
        return None

# -----------------------
# Enhanced LittleFS Data Logger
# -----------------------

class Logger:
    def append(self, filename, data):
        """Append a new record as a separate JSON line with formatted timestamp."""
        t = time.localtime()
        timestamp = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(t[0], t[1], t[2], t[3], t[4], t[5])
        log_entry = {
            "timestamp": timestamp,
            "data": data
        }
        with open(filename, 'a') as f:
            f.write(ujson.dumps(log_entry) + "\n")

    def read_lines(self, filename):
        """Read all JSON objects from a file line by line."""
        logs = []
        if filename in os.listdir():
            with open(filename) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        logs.append(ujson.loads(line))
                    except ValueError:
                        print("Skipping invalid JSON line:", line)
        return logs

    def exists(self, filename):
        return filename in os.listdir()

    def delete(self, filename):
        if self.exists(filename):
            os.remove(filename)

    def list_files(self):
        return os.listdir()
# -----------------------
# Wi-Fi Manager
# -----------------------

class WiFi:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

    def connect(self, ssid, password, timeout=15):
        """
        Connect to Wi-Fi.
        timeout: seconds to wait before giving up
        Returns IP info if connected, else None.
        """
        if self.wlan.isconnected():
            return self.wlan.ifconfig()  # Already connected

        self.wlan.connect(ssid, password)
        start = time.time()
        while not self.wlan.isconnected():
            if (time.time() - start) > timeout:
                return None  # Timeout
            time.sleep(0.5)
        return self.wlan.ifconfig()

    def disconnect(self):
        """Disconnect Wi-Fi."""
        self.wlan.disconnect()

    def is_connected(self):
        """Check connection status."""
        return self.wlan.isconnected()

    def scan(self):
        """Return a list of available SSIDs."""
        return [net[0].decode() for net in self.wlan.scan()]

    def auto_reconnect(self, ssid, password, attempts=3):
        """
        Try reconnecting automatically.
        Returns True if connected, False otherwise.
        """
        for _ in range(attempts):
            if self.connect(ssid, password):
                return True
            time.sleep(2)
        return False

# -----------------------
# GUVA_S12SD Wrapper
# -----------------------

class GUVA_S12SD:
    """Simple wrapper for the GUVA-S12SD UV sensor (analog)."""
    def __init__(self, pin=34):
        self.adc = ADC(Pin(pin))
        self.adc.atten(ADC.ATTN_11DB)  # full range 0–3.6V
        self.adc.width(ADC.WIDTH_12BIT)  # 0–4095

    def raw(self):
        """Return the raw ADC value (0–4095)."""
        return self.adc.read()

    def voltage(self):
        """Return voltage at the sensor pin in volts."""
        return self.adc.read() / 4095 * 3.3  # ESP32 ADC reference ~3.3V

    def uv_index(self):
        """
        Convert voltage to approximate UV index.
        GUVA-S12SD outputs ~0.0–2.0V for 0–15 mW/cm².
        Approximate formula: UV index ≈ (Vout - 0.99)/0.1
        """
        v = self.voltage()
        uv = max(0, (v - 0.99) / 0.1)  # clamp negative to 0
        return round(uv, 1)

# -----------------------
# MQTT Client
# -----------------------

class MQTT:
    def __init__(self, client_id, broker, port=1883, keepalive=60):
        """
        client_id: unique ID for the MQTT client
        broker: IP or hostname of broker
        port: MQTT port (default 1883)
        keepalive: keepalive interval in seconds
        """
        self.client = MQTTClient(client_id, broker, port=port, keepalive=keepalive)
        self.connected = False

    def connect(self):
        """Connect to the MQTT broker."""
        try:
            self.client.connect()
            self.connected = True
        except Exception as e:
            print("MQTT connect failed:", e)
            self.connected = False

    def publish(self, topic, message, is_json=False):
        """
        Publish a message to a topic.
        is_json: if True, serializes the message as JSON
        """
        if not self.connected:
            self.connect()
        try:
            if is_json:
                import ujson
                message = ujson.dumps(message)
            self.client.publish(topic, message)
        except Exception as e:
            print("MQTT publish failed:", e)

    def subscribe(self, topic, callback):
        """Subscribe to a topic with a callback function."""
        try:
            self.client.set_callback(callback)
            self.client.subscribe(topic)
        except Exception as e:
            print("MQTT subscribe failed:", e)

    def check_msg(self):
        """Check for incoming messages."""
        try:
            self.client.check_msg()
        except Exception as e:
            print("MQTT check_msg error:", e)

    def disconnect(self):
        """Disconnect from the broker."""
        try:
            self.client.disconnect()
            self.connected = False
        except Exception as e:
            print("MQTT disconnect failed:", e)



