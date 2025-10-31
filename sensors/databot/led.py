# python
from machine import Pin
import neopixel
from time import sleep # needed for this test only
import time

class DatabotLED:
    def __init__(self, pin=2, num_leds=3):
        self.pin = pin
        self.num_leds = num_leds
        self.np = neopixel.NeoPixel(Pin(self.pin), self.num_leds)
        self.colors = [(0, 0, 0)] * num_leds  # Store current colors

    def _scale_color(self, color, brightness):
        """Scale color (R,G,B) by brightness percentage (0–100)."""
        scale = max(0, min(100, brightness)) / 100
        return tuple(int(c * scale) for c in color)

    def set_color(self, index, r, g, b, brightness=100):
        """Set color and brightness of one LED (index 0–2)."""
        if not 0 <= index < self.num_leds:
            raise IndexError("LED index out of range")

        adjusted = self._scale_color((r, g, b), brightness)
        self.colors[index] = adjusted
        self.np[index] = adjusted
        self.np.write()

        # Example: You could trigger the buzzer here for feedback
        # buzzer.beep(1000, 0.2, 70)  # freq=1000Hz, 0.2s, 70% volume

    def set_all(self, r, g, b, brightness=100):
        """Set all LEDs to same color and brightness."""
        adjusted = self._scale_color((r, g, b), brightness)
        for i in range(self.num_leds):
            self.colors[i] = adjusted
            self.np[i] = adjusted
        self.np.write()

        # Example: Buzzer could beep once when all LEDs change
        # buzzer.beep(1500, 0.1)

    def clear(self):
        """Turn off all LEDs."""
        self.np.fill((0, 0, 0))
        self.np.write()
        self.colors = [(0, 0, 0)] * self.num_leds

        # Example: Beep low tone when clearing LEDs
        # buzzer.beep(500, 0.1)
        
    def rainbow_transition(self, delay=0.02, duration=10):
        c_time = 0
        """Continuously cycles all LEDs through rainbow hues."""
        def wheel(pos):
            # Generates colors across a color wheel (0–255)
            if pos < 85:
                return (int(pos * 3), int(255 - pos * 3), 0)
            elif pos < 170:
                pos -= 85
                return (int(255 - pos * 3), 0, int(pos * 3))
            else:
                pos -= 170
                return (0, int(pos * 3), int(255 - pos * 3))

        offset = [0, 85, 170]                                                                    # start positions for the 3 LEDs
        while c_time <= duration:
            sleep(0.1)
            c_time += 1
            for j in range(256):
                for i in range(self.num_leds):
                    idx = (j + offset[i]) % 256
                    r, g, b = wheel(idx)
                    self.set_color(i, r, g, b)
                time.sleep(delay)

leds = DatabotLED()



for _ in range(5):
    leds.set_all(10, 240, 10, brightness=10)
    sleep(0.5)
    leds.clear()
    sleep(0.4)

leds.set_color(0, 255, 0, 0, 70) 

leds.set_color(1, 0, 255, 0, 70) 
leds.set_color(2, 0, 0, 255, 70)  
sleep(0.2)
leds.clear()

leds.rainbow_transition(0.05)

