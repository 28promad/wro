# micropython
import sys

def send_to_pi(message: str):
    """Send a message to the Raspberry Pi."""
    print(message, flush=True)

def read_from_pi():
    """Read a message from the Raspberry Pi."""
    try:
        line = sys.stdin.readline()
        if line:
            # Clean and standardize the input
            return line.strip().replace("'", "").replace('"', "")
        return None
    except Exception as e:
        print("Error reading from Pi:", e)
        return None


