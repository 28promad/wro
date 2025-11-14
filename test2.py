# python
# test_databot_from_laptop.py (revised)
import serial, json, time

PORT = "/dev/ttyUSB0"   # Change if needed
BAUDRATE = 9600

def main():
    print(f"Connecting to Databot on {PORT}...")
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    time.sleep(2)  # Allow Databot to boot/restart

    print("Sending 'Start'...")
    ser.write(b"Start")  # <-- no newline
    time.sleep(0.5)

    # Try again with newline, just in case
    ser.write(b"\n")

    while True:
        try:
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                print("\n✅ Data received:")
                for k, v in data.items():
                    print(f"  {k:<5}: {v}")
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
