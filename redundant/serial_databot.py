# micropython
import sys

def send_to_pi(message: str):
    """Send a message to the Raspberry Pi."""
    print(message)

def read_from_pi():
    """Read a message from the Raspberry Pi."""
    line = sys.stdin.readline()
    return line.strip() if line else None


