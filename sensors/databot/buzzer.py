# python
from machine import Pin, PWM
from time import sleep

class DatabotBuzzer:
    def __init__(self, pin=32):
        self.pin = pin
        self.pwm = PWM(Pin(self.pin))
        self.pwm.duty(0)  # Start silent

    def beep(self, freq=1000, duration=0.2, volume=100):
        """
        Play a single beep.
        :param freq: frequency in Hz (e.g., 440 for A4 note)
        :param duration: duration in seconds
        :param volume: 0–100, controls PWM duty cycle
        """
        duty = int(1023 * (max(0, min(100, volume)) / 100))
        self.pwm.freq(freq)
        self.pwm.duty(duty)
        sleep(duration)
        self.pwm.duty(0)  # Stop tone

    def play_tone(self, freq=1000, volume=80):
        """Continuously play a tone until stopped."""
        duty = int(1023 * (max(0, min(100, volume)) / 100))
        self.pwm.freq(freq)
        self.pwm.duty(duty)

    def stop(self):
        """Stop any sound."""
        self.pwm.duty(0)

    def deinit(self):
        """Release the PWM resource."""
        self.pwm.deinit()

# example usage
"""
buzzer = DatabotBuzzer()

buzzer.beep(freq=1500, duration=0.2)
sleep(0.5)
buzzer.beep(1500, 1, 10)
sleep(0.5)
buzzer.beep(1500, 1, 20)
sleep(0.5)
buzzer.beep(1500, 1, 30)
sleep(0.5)
buzzer.beep(1500, 1, 40)
sleep(0.5)
buzzer.stop()
"""