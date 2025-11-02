# python
# test_databot_from_laptop.py
import serial, json, time

# --- Change this to your Databot port ---
PORT = "/dev/ttyUSB0"   # e.g. "COM3" on Windows
BAUDRATE = 115200

def main():
    print(f"Connecting to Databot on {PORT}...")
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    time.sleep(2)  # allow Databot to reboot if needed

    print("Sending Start command...")
    ser.write(b"Start\n")

    while True:
        try:
            line = ser.readline().decode().strip()
            if not line:
                continue

            # Try parsing JSON from Databot
            try:
                data = json.loads(line)
                print("\n✅ Received data:")
                for k, v in data.items():
                    print(f"  {k:<6}: {v}")
            except json.JSONDecodeError:
                print("Raw:", line)

        except KeyboardInterrupt:
            print("\nStopping...")
            ser.write(b"Stop\n")
            break
        except Exception as e:
            print("Error:", e)
            break

    ser.close()

if __name__ == "__main__":
    main()
