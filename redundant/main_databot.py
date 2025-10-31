from databoot import Lights, Buzzer, Humidity, AirQualitySensor
from comms import serial_databot
from time import sleep

# Initialize all components
lights = Lights(num_leds=3, pin=2)  # 3 LEDs on pin 2
buzzer = Buzzer(pin=32)
humidity_sensor = Humidity()  # Uses default I2C pins
air_sensor = AirQualitySensor()  # Uses default I2C pins

def blink_leds(r, g, b, times=3):
    """Helper function to blink LEDs"""
    for _ in range(times):
        lights.set_all(r, g, b)
        sleep(0.5)
        lights.off()
        sleep(0.5)

def parse_command(cmd):
    """Parse commands from Pi"""
    try:
        if cmd.startswith('led'):
            # Format: led0:(r,g,b,brightness)
            led_num = int(cmd[3])
            color_start = cmd.find('(') + 1
            color_end = cmd.find(')')
            r, g, b, brightness = map(int, cmd[color_start:color_end].split(','))
            # Convert brightness from 0-100 to 0-1.0
            brightness = brightness / 100.0
            lights.set_brightness(brightness)
            lights.set_one(led_num, r, g, b)
        elif cmd.startswith('buzzer'):
            # Format: buzzer:(tone,volume)
            params_start = cmd.find('(') + 1
            params_end = cmd.find(')')
            tone, volume = map(int, cmd[params_start:params_end].split(','))
            buzzer.beep(tone, 200)  # Fixed 200ms duration
    except Exception as e:
        print(f"Error parsing command: {e}")

lights.set_all(255, 0, 0)
connection_attempts = 0
max_attempts = 3
handshake_complete = False

while connection_attempts < max_attempts and not handshake_complete:
    sleep(1)
    msg = serial_databot.read_from_pi()
    if msg == "Start":
        serial_databot.send_to_pi("ready")
        # Wait for ack
        for _ in range(5):
            ack = serial_databot.read_from_pi()
            if ack == "ack":
                handshake_complete = True
                break
            sleep(1)
    connection_attempts += 1

if handshake_complete:
    sleep(0.5)
    blink_leds(0, 255, 0)
    # Main loop
    while True:
        try:
            # Get sensor readings
            temp, humidity = humidity_sensor.read()
            co2 = air_sensor.read_co2()
            tvoc = air_sensor.read_voc()

            # Ensure all values are valid numbers
            temp = temp if temp is not None else 0.0
            humidity = humidity if humidity is not None else 0.0
            co2 = co2 if co2 is not None else 0.0
            tvoc = tvoc if tvoc is not None else 0.0


            # Send sensor data to Pi in simplified format
            sensor_data = f"S|{float(temp):.1f},{float(humidity):.1f},{float(co2)},{float(tvoc)}"
            serial_databot.send_to_pi(sensor_data)

            # Check for commands from Pi in simplified format
            command = serial_databot.read_from_pi()
            if command:
                # LED: L|num,r,g,b,bright
                # Buzzer: B|tone,vol
                try:
                    if command.startswith('L|'):
                        parts = command[2:].split(',')
                        led_num, r, g, b, brightness = map(int, parts)
                        lights.set_brightness(brightness / 100.0)
                        lights.set_one(led_num, r, g, b)
                    elif command.startswith('B|'):
                        tone, volume = map(int, command[2:].split(','))
                        buzzer.beep(tone, 200)
                except Exception as e:
                    print(f"Error parsing command: {e}")

            sleep(0.1)

        except Exception as e:
            print(f"Error in main loop: {e}")
            blink_leds(255, 0, 0)  # Blink red to indicate error
            continue
            
else:
    # If connection failed after max attempts, stay red
    lights.set_all(255, 0, 0)