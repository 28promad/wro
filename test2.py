# python
from machine import Pin
import neopixel
from time import sleep

np = neopixel.NeoPixel(Pin(2), 3)

while True:
    for brightness in range(0, 256, 10):
        np.fill((30, 12, 3))
        np.write()
        sleep(0.05)
