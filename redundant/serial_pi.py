# python
import serial

ser = None

def initialise(port: str, baudrate: int = 115200):
    """Initialise serial communication with Databot."""
    global ser
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"[OK] Connected to Databot on {port} at {baudrate} baud.")
        return ser
    except serial.SerialException as e:
        print(f"[Error] Could not open {port}: {e}")
        ser = None
        return None


def send_to_databot(message: str):
    """Send a message to the Databot."""
    if ser and ser.is_open:
        ser.write((message + '\n').encode())
    else:
        print("[Error] Serial not initialised or closed.")


def read_from_databot():
    """Read a message from the Databot (if available)."""
    if ser and ser.in_waiting:
        return ser.readline().decode().strip()
    return None
