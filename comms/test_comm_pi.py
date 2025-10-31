from comms import serial_pi
from time import sleep

def test_serial_comm():
    # Initialize serial connection
    print("Initializing serial connection...")
    serial_pi.initialise('/dev/ttyUSB0')
    
    # Send start signal
    print("Sending start signal...")
    serial_pi.send_to_databot("Start")
    sleep(1)
    
    # Test sequence
    print("Starting test sequence...")
    
    # Test LED pattern
    commands = [
        'led0:(255,0,0,100)',    # Red
        'led1:(0,255,0,100)',    # Green
        'led2:(0,0,255,100)',    # Blue
        'buzzer:(1000,80)',      # Buzzer beep
        'led0:(0,0,0,0)',        # Turn off LEDs
        'led1:(0,0,0,0)',
        'led2:(0,0,0,0)'
    ]
    
    for cmd in commands:
        print(f"Sending command: {cmd}")
        serial_pi.send_to_databot(cmd)
        # Wait for response
        response = serial_pi.read_from_databot()
        print(f"Response: {response}")
        sleep(0.5)

if __name__ == "__main__":
    try:
        test_serial_comm()
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"Error during test: {e}")
