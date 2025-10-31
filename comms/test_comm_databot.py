from databoot import Lights, Buzzer
from comms import serial_databot
from time import sleep

# Initialize components
lights = Lights(num_leds=3, pin=2)  # 3 LEDs on pin 2
buzzer = Buzzer(pin=32)

print("Databot test: waiting for Pi command...")

while True:
    cmd = serial_databot.read_from_pi()
    if cmd:
        print(f"Received command: {cmd}")
        try:
            if cmd == "Start":
                print("Connection established")
                serial_databot.send_to_pi("ready")
            
            elif cmd.startswith('led'):
                # Format: led0:(r,g,b,brightness)
                led_num = int(cmd[3])
                color_start = cmd.find('(') + 1
                color_end = cmd.find(')')
                r, g, b, brightness = map(int, cmd[color_start:color_end].split(','))
                # Convert brightness from 0-100 to 0-1.0
                brightness = brightness / 100.0
                lights.set_brightness(brightness)
                lights.set_one(led_num, r, g, b)
                serial_databot.send_to_pi(f"done:{cmd}")
                
            elif cmd.startswith('buzzer'):
                # Format: buzzer:(tone,volume)
                params_start = cmd.find('(') + 1
                params_end = cmd.find(')')
                tone, volume = map(int, cmd[params_start:params_end].split(','))
                buzzer.beep(tone, 200)  # 200ms duration
                serial_databot.send_to_pi(f"done:{cmd}")
                
        except Exception as e:
            print(f"Error processing command: {e}")
            serial_databot.send_to_pi(f"error:{str(e)}")
        
        sleep(0.1)  # Small delay between commands
