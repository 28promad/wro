# main_pi.py
from comms import serial_pi
import time

def run_pi_main():
    serial_pi.initialise('/dev/ttyUSB0')
    print("Sending start signal...")
    serial_pi.send_to_databot("Start")

    last_ping_time = time.time()

    while True:
        msg = serial_pi.read_from_databot()
        if msg:
            print("Databot →", msg)

        # Send a ping every 10 seconds just to check connectivity
        if time.time() - last_ping_time > 10:
            serial_pi.send_to_databot("ping")
            last_ping_time = time.time()

        time.sleep(0.1)

if __name__ == "__main__":
    try:
        run_pi_main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
