import serial
import time

ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)

def send_to_databot(message):
    ser.write((message + "\n").encode())

def read_from_databot():
    if ser.in_waiting:
        return ser.readline().decode().strip()

    return None

# Example while loop
while True:
    if ser.in_waiting:
        line = ser.readline().decode().strip()
        print(line)


