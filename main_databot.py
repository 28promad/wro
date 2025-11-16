# main_databot.py
from databoot import Lights, Buzzer, AirQualitySensor, Humidity
from ble_databot import BLE_UART
from machine import I2C, Pin
from imu_icm20948 import ICM20948
import time, ujson
from math import sqrt, atan2, sin, cos, radians

# --- Hardware setup ---

lights = Lights(num_leds=3, pin=2)
buzzer = Buzzer(pin=32)
air = AirQualitySensor()
hum = Humidity()

# IMU (ICM-20948 at address 0x68)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
imu = ICM20948(i2c, addr=0x68)

# --- Threshold constants ---
CO2_LIMIT = 1000
VOC_LIMIT = 400
TEMP_LIMIT = 30
HUM_MIN, HUM_MAX = 30, 70

# --- Kinematics & Mapping Constants ---
G_FORCE = 9.81              # Approximate gravity m/s^2
COMP_FILTER_ALPHA = 0.98    # 98% gyro, 2% accel
ACCEL_DEADZONE = 0.08       # m/s^2, ignore tiny jitters (increased for rough terrain)
VELOCITY_DAMPING = 0.98     # Artificial friction to reduce drift

# --- Kinematics & Mapping variables ---
# These are the rover's "state"
velocity_forward = 0.0      # Estimated forward velocity (m/s)
pos_x = 0.0                 # 2D map position X (meters)
pos_y = 0.0                 # 2D map position Y (meters)
pitch = 0.0                 # Vehicle's pitch angle (radians)
yaw = 0.0                   # Vehicle's heading/yaw angle (radians)
prev_time = time.ticks_ms() # Used for integration time step (dt)

# ----------------------  Helper functions  ----------------------
def wait_for_connection():
    """Wait for 'Start' command from the Raspberry Pi."""
    lights.set_all(255, 240, 224)
    print("Waiting for Raspberry Pi...")
    ble = BLE_UART(name="databot-uart")
    started = False

    def on_receive(data):
        nonlocal started
        try:
            msg = data.decode('utf-8')
        except Exception:
            msg = repr(data)

        if msg == "Start":
            for _ in range(3):
                lights.set_all(0, 255, 0)
                time.sleep(0.3)
                lights.off()
                time.sleep(0.3)
            lights.set_all(0, 255, 0)
            ble.send("ready")
            print("Connected to Pi via BLE!")
            started = True

    ble.on_receive(on_receive)
    ble.start_advertising()

    while not started:
        time.sleep(0.1)
    
    # IMPORTANT: Set the initial time *after* connection
    # to start kinematics calculation from 0
    global prev_time
    prev_time = time.ticks_ms()
    return ble

def read_environment():
    co2 = air.read_co2() or 0
    voc = air.read_voc() or 0
    temp, humi = hum.read()
    return co2, voc, temp or 0, humi or 0

def read_imu():
    # Read all 6 axes from the IMU
    ax, ay, az = imu.accel()
    gx, gy, gz = imu.gyro()
    
    # Convert gyro from deg/s to rad/s for math
    # ICM20948 default is +/- 250 dps
    # (Check your library, this factor might be different!)
    # Assuming the library 'imu.gyro()' already returns rad/s.
    # If it returns deg/s, you MUST convert:
    # gx = radians(gx)
    # gy = radians(gy)
    # gz = radians(gz)
    # For now, we'll assume they are in rad/s.
    
    return ax, ay, az, gx, gy, gz

def update_kinematics(ax, ay, az, gx, gy, gz):
    """
    Estimate 2D displacement (m) and heading by removing gravity.
    This function is called as fast as possible in the main loop.
    """
    global velocity_forward, pos_x, pos_y, pitch, yaw, prev_time

    # --- 1. Calculate Time Delta (dt) ---
    now = time.ticks_ms()
    dt = time.ticks_diff(now, prev_time) / 1000.0
    if dt <= 0: # Avoid division by zero
        return
    prev_time = now

    # --- 2. Update Pitch (Complementary Filter) ---
    # This finds the rover's tilt to remove gravity from 'ax'
    try:
        # Angle from accelerometer (stable, but noisy)
        # Uses atan2 to find pitch from gravity vector
        pitch_accel = atan2(ax, sqrt(ay**2 + az**2))
    except Exception:
        pitch_accel = pitch # Use last value if math fails

    # Angle from gyroscope (fast, but drifts)
    pitch_gyro = pitch + gy * dt # gy is pitch rate
    
    # Fuse: 98% gyro, 2% accel
    pitch = (COMP_FILTER_ALPHA * pitch_gyro) + ((1.0 - COMP_FILTER_ALPHA) * pitch_accel)

    # --- 3. Update Yaw (Heading) ---
    # Simple integration of yaw rate (gz).
    # This WILL drift over time, but is the simplest way to track turns.
    # For better results, you'd fuse this with a magnetometer.
    yaw += gz * dt
    
    # --- 4. Calculate Linear Forward Acceleration ---
    # This is the key: remove the gravity component from 'ax'
    # ax_linear = (raw 'ax') - (gravity pulling on 'ax')
    ax_linear = ax - (G_FORCE * sin(pitch))
    
    # --- 5. Integrate for Displacement (Double Integration) ---
    if abs(ax_linear) < ACCEL_DEADZONE:
        ax_linear = 0.0
        # If we're not accelerating, dampen velocity to stop drift
        velocity_forward *= VELOCITY_DAMPING 
    
    velocity_forward += ax_linear * dt
    velocity_forward *= VELOCITY_DAMPING # Apply damping
    
    displacement_step = velocity_forward * dt
    
    # --- 6. Update 2D Map Position ---
    # Project the forward displacement onto the 2D map using the current yaw
    pos_x += displacement_step * cos(yaw)
    pos_y += displacement_step * sin(yaw)
    # pos_x, pos_y, and yaw are now updated and ready for send_data to read

def status_feedback(co2, voc, temp, hum):
    """Update LEDs and buzzer according to environmental safety."""
    if co2 > CO2_LIMIT or voc > VOC_LIMIT:
        lights.set_one(0, 255, 0, 0)
        buzzer.beep(800, 100)
    else:
        lights.set_one(0, 0, 255, 0)
    if temp > TEMP_LIMIT:
        lights.set_one(1, 255, 0, 0)
    else:
        lights.set_one(1, 0, 255, 0)
    if hum < HUM_MIN or hum > HUM_MAX:
        lights.set_one(2, 255, 0, 0)
    else:
        lights.set_one(2, 0, 255, 0)

def send_data(ble=None):
    """
    Gather all sensor readings and latest KINEMATICS, and send as JSON.
    This function just *reads* the global kinematics variables.
    """
    global pos_x, pos_y, yaw # Access the latest values
    
    co2, voc, temp, hum = read_environment()
    ax, ay, az, gx, gy, gz = read_imu() # Get current IMU for JSON
    
    # Get the latest kinematics calculated by the main loop
    px, py, heading = pos_x, pos_y, yaw
    
    data = {
        "co2": co2, "voc": voc, "temp": temp, "hum": hum,
        "ax": ax, "ay": ay, "az": az,       # Raw IMU data
        "gx": gx, "gy": gy, "gz": gz,
        "pos_x": px,    # NEW: 2D map X
        "pos_y": py,    # NEW: 2D map Y
        "yaw": heading  # NEW: Rover heading (radians)
    }

    payload = ujson.dumps(data)
    if ble:
        ble.send(payload)
    else:
        # Fallback: print (or you can buffer locally)
        print("Data:", payload)
    
    status_feedback(co2, voc, temp, hum)

# ----------------------  Main loop  ----------------------
def main():
    ble = wait_for_connection()
    last_send = time.ticks_ms()

    try:
        while True:
            # --- CRITICAL CHANGE ---
            # Update kinematics as fast as possible in the main loop
            # This is essential for accurate integration (small dt)
            ax, ay, az, gx, gy, gz = read_imu()
            update_kinematics(ax, ay, az, gx, gy, gz)
            
            # Only send the data to the Pi every 1 second
            if time.ticks_diff(time.ticks_ms(), last_send) > 1000:
                send_data(ble=ble)
                last_send = time.ticks_ms()
                
            time.sleep(0.02) # Loop at 50Hz (dt = 20ms)
            
    except KeyboardInterrupt:
        lights.off()


if __name__ == "__main__":
    main()
