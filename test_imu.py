#!/usr/bin/env python3
# test_databot_imu.py
# Test tool to read IMU data from databot via Bluetooth
# Tests accelerometer, gyroscope, heading, pitch, roll, and incline

import asyncio
import json
import time
import math
from comms.central import BLE_UART_Central

# ---------------- IMU Visualizer ----------------
class IMUVisualizer:
    """Real-time IMU data visualization."""
    
    def __init__(self):
        self.latest_data = {}
        self.sample_count = 0
        self.start_time = time.time()
        
        # Statistics
        self.pitch_samples = []
        self.roll_samples = []
        self.yaw_samples = []
        self.incline_samples = []
        
    def update(self, data):
        """Update with new sensor data."""
        self.latest_data = data
        self.sample_count += 1
        
        # Collect statistics
        if 'pitch' in data and data['pitch'] is not None:
            self.pitch_samples.append(data['pitch'])
            if len(self.pitch_samples) > 100:
                self.pitch_samples.pop(0)
        
        if 'roll' in data and data['roll'] is not None:
            self.roll_samples.append(data['roll'])
            if len(self.roll_samples) > 100:
                self.roll_samples.pop(0)
        
        if 'yaw' in data and data['yaw'] is not None:
            self.yaw_samples.append(data['yaw'])
            if len(self.yaw_samples) > 100:
                self.yaw_samples.pop(0)
        
        if 'incline' in data and data['incline'] is not None:
            self.incline_samples.append(data['incline'])
            if len(self.incline_samples) > 100:
                self.incline_samples.pop(0)
    
    def display_raw(self):
        """Display raw accelerometer and gyroscope readings."""
        print("\n" + "="*70)
        print("                    RAW IMU DATA")
        print("="*70)
        
        # Accelerometer
        ax = self.latest_data.get('ax', 0.0)
        ay = self.latest_data.get('ay', 0.0)
        az = self.latest_data.get('az', 0.0)
        
        print(f"\n📊 Accelerometer (m/s²):")
        print(f"  X: {ax:7.3f}  {'█' * int(abs(ax) * 5)}")
        print(f"  Y: {ay:7.3f}  {'█' * int(abs(ay) * 5)}")
        print(f"  Z: {az:7.3f}  {'█' * int(abs(az) * 5)}")
        
        # Gyroscope
        gx = self.latest_data.get('gx', 0.0)
        gy = self.latest_data.get('gy', 0.0)
        gz = self.latest_data.get('gz', 0.0)
        
        print(f"\n🔄 Gyroscope (rad/s):")
        print(f"  X: {gx:7.3f}  {'█' * int(abs(gx) * 20)}")
        print(f"  Y: {gy:7.3f}  {'█' * int(abs(gy) * 20)}")
        print(f"  Z: {gz:7.3f}  {'█' * int(abs(gz) * 20)}")
        
        # Magnitude
        accel_mag = math.sqrt(ax**2 + ay**2 + az**2)
        gyro_mag = math.sqrt(gx**2 + gy**2 + gz**2)
        
        print(f"\n📏 Magnitude:")
        print(f"  Accel: {accel_mag:7.3f} m/s²")
        print(f"  Gyro:  {gyro_mag:7.3f} rad/s")
    
    def display_orientation(self):
        """Display calculated orientation (pitch, roll, yaw, incline)."""
        print("\n" + "="*70)
        print("                    ORIENTATION")
        print("="*70)
        
        pitch = self.latest_data.get('pitch', 0.0)
        roll = self.latest_data.get('roll', 0.0)
        yaw = self.latest_data.get('yaw', 0.0)
        incline = self.latest_data.get('incline', 0.0)
        
        # Convert to degrees
        pitch_deg = math.degrees(pitch) if pitch else 0.0
        roll_deg = math.degrees(roll) if roll else 0.0
        yaw_deg = math.degrees(yaw) if yaw else 0.0
        incline_deg = math.degrees(incline) if incline else 0.0
        
        print(f"\n🧭 Heading (Yaw):  {yaw_deg:6.1f}°  {self._get_direction(yaw_deg)}")
        print(f"↕️  Pitch:         {pitch_deg:6.1f}°  {self._get_pitch_desc(pitch_deg)}")
        print(f"↔️  Roll:          {roll_deg:6.1f}°  {self._get_roll_desc(roll_deg)}")
        print(f"⛰️  Incline:       {incline_deg:6.1f}°  {self._get_incline_desc(incline_deg)}")
        
        # Visual indicators
        print(f"\n📐 Tilt Indicator:")
        self._draw_tilt_indicator(pitch_deg, roll_deg)
        
        # Compass
        print(f"\n🧭 Compass:")
        self._draw_compass(yaw_deg)
    
    def _get_direction(self, yaw_deg):
        """Get cardinal direction from yaw."""
        yaw_deg = (yaw_deg + 360) % 360
        
        if yaw_deg >= 337.5 or yaw_deg < 22.5:
            return "N  (North)"
        elif yaw_deg >= 22.5 and yaw_deg < 67.5:
            return "NE (Northeast)"
        elif yaw_deg >= 67.5 and yaw_deg < 112.5:
            return "E  (East)"
        elif yaw_deg >= 112.5 and yaw_deg < 157.5:
            return "SE (Southeast)"
        elif yaw_deg >= 157.5 and yaw_deg < 202.5:
            return "S  (South)"
        elif yaw_deg >= 202.5 and yaw_deg < 247.5:
            return "SW (Southwest)"
        elif yaw_deg >= 247.5 and yaw_deg < 292.5:
            return "W  (West)"
        else:
            return "NW (Northwest)"
    
    def _get_pitch_desc(self, pitch_deg):
        """Get pitch description."""
        if abs(pitch_deg) < 5:
            return "Level"
        elif pitch_deg > 0:
            return "Nose Up"
        else:
            return "Nose Down"
    
    def _get_roll_desc(self, roll_deg):
        """Get roll description."""
        if abs(roll_deg) < 5:
            return "Level"
        elif roll_deg > 0:
            return "Leaning Right"
        else:
            return "Leaning Left"
    
    def _get_incline_desc(self, incline_deg):
        """Get incline description."""
        if incline_deg < 5:
            return "Flat"
        elif incline_deg < 15:
            return "Slight Slope"
        elif incline_deg < 30:
            return "Moderate Slope"
        else:
            return "Steep Slope"
    
    def _draw_tilt_indicator(self, pitch, roll):
        """Draw ASCII tilt indicator."""
        # Normalize to -1 to 1
        px = max(-1, min(1, pitch / 30))
        rx = max(-1, min(1, roll / 30))
        
        # Draw grid
        for y in range(5, -6, -1):
            line = "  "
            for x in range(-5, 6):
                # Center indicator position
                ix = int(rx * 5)
                iy = int(px * 5)
                
                if x == 0 and y == 0:
                    line += "+"
                elif x == ix and y == iy:
                    line += "●"
                elif x == 0:
                    line += "│"
                elif y == 0:
                    line += "─"
                else:
                    line += " "
            print(line)
    
    def _draw_compass(self, yaw_deg):
        """Draw ASCII compass."""
        # Normalize to 0-360
        yaw_deg = (yaw_deg + 360) % 360
        
        # Simple compass rose
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        angles = [0, 45, 90, 135, 180, 225, 270, 315]
        
        # Find closest direction
        closest_idx = min(range(len(angles)), key=lambda i: abs(angles[i] - yaw_deg))
        
        compass_line = "  "
        for i, d in enumerate(dirs):
            if i == closest_idx:
                compass_line += f"[{d}]"
            else:
                compass_line += f" {d} "
            if i < len(dirs) - 1:
                compass_line += " "
        
        print(compass_line)
    
    def display_statistics(self):
        """Display statistical summary."""
        print("\n" + "="*70)
        print("                    STATISTICS")
        print("="*70)
        
        runtime = time.time() - self.start_time
        rate = self.sample_count / runtime if runtime > 0 else 0
        
        print(f"\n📊 Data Collection:")
        print(f"  Samples: {self.sample_count}")
        print(f"  Runtime: {runtime:.1f}s")
        print(f"  Rate: {rate:.1f} Hz")
        
        if self.pitch_samples:
            pitch_avg = sum(self.pitch_samples) / len(self.pitch_samples)
            pitch_min = min(self.pitch_samples)
            pitch_max = max(self.pitch_samples)
            
            print(f"\n↕️  Pitch (last 100 samples):")
            print(f"  Average: {math.degrees(pitch_avg):6.2f}°")
            print(f"  Range:   {math.degrees(pitch_min):6.2f}° to {math.degrees(pitch_max):6.2f}°")
        
        if self.roll_samples:
            roll_avg = sum(self.roll_samples) / len(self.roll_samples)
            roll_min = min(self.roll_samples)
            roll_max = max(self.roll_samples)
            
            print(f"\n↔️  Roll (last 100 samples):")
            print(f"  Average: {math.degrees(roll_avg):6.2f}°")
            print(f"  Range:   {math.degrees(roll_min):6.2f}° to {math.degrees(roll_max):6.2f}°")
        
        if self.incline_samples:
            incline_avg = sum(self.incline_samples) / len(self.incline_samples)
            incline_max = max(self.incline_samples)
            
            print(f"\n⛰️  Incline (last 100 samples):")
            print(f"  Average: {math.degrees(incline_avg):6.2f}°")
            print(f"  Maximum: {math.degrees(incline_max):6.2f}°")

# ---------------- Test Modes ----------------
async def test_raw_imu(duration=10):
    """Test mode: Display raw IMU readings."""
    print("\n" + "="*70)
    print("           RAW IMU TEST MODE")
    print("="*70)
    print(f"\nReading IMU data for {duration} seconds...")
    print("Press Ctrl+C to stop early\n")
    
    central = BLE_UART_Central()
    visualizer = IMUVisualizer()
    ready_event = asyncio.Event()
    
    def on_receive(data_bytes: bytes):
        try:
            text = data_bytes.decode('utf-8')
        except Exception:
            return
        
        if isinstance(text, str) and text.strip().lower() == 'ready':
            ready_event.set()
            return
        
        try:
            data = json.loads(text)
            visualizer.update(data)
        except Exception:
            pass
    
    central.on_receive(on_receive)
    
    print("Connecting to databot...")
    if not await central.connect():
        print("❌ Failed to connect")
        return
    
    await central.send('Start')
    
    try:
        await asyncio.wait_for(ready_event.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pass
    
    print("✓ Connected\n")
    
    start_time = time.time()
    last_display = 0
    
    try:
        while time.time() - start_time < duration:
            await asyncio.sleep(0.1)
            
            # Update display every 0.5 seconds
            if time.time() - last_display > 0.5:
                import os
                os.system('clear' if os.name != 'nt' else 'cls')
                visualizer.display_raw()
                last_display = time.time()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
    
    finally:
        if central.is_connected:
            await central.disconnect()
        
        visualizer.display_statistics()

async def test_orientation(duration=10):
    """Test mode: Display orientation (pitch, roll, yaw, incline)."""
    print("\n" + "="*70)
    print("           ORIENTATION TEST MODE")
    print("="*70)
    print(f"\nReading orientation data for {duration} seconds...")
    print("Tilt the databot to see changes")
    print("Press Ctrl+C to stop early\n")
    
    central = BLE_UART_Central()
    visualizer = IMUVisualizer()
    ready_event = asyncio.Event()
    
    def on_receive(data_bytes: bytes):
        try:
            text = data_bytes.decode('utf-8')
        except Exception:
            return
        
        if isinstance(text, str) and text.strip().lower() == 'ready':
            ready_event.set()
            return
        
        try:
            data = json.loads(text)
            visualizer.update(data)
        except Exception:
            pass
    
    central.on_receive(on_receive)
    
    print("Connecting to databot...")
    if not await central.connect():
        print("❌ Failed to connect")
        return
    
    await central.send('Start')
    
    try:
        await asyncio.wait_for(ready_event.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pass
    
    print("✓ Connected\n")
    
    start_time = time.time()
    last_display = 0
    
    try:
        while time.time() - start_time < duration:
            await asyncio.sleep(0.1)
            
            if time.time() - last_display > 0.5:
                import os
                os.system('clear' if os.name != 'nt' else 'cls')
                visualizer.display_orientation()
                last_display = time.time()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
    
    finally:
        if central.is_connected:
            await central.disconnect()
        
        visualizer.display_statistics()

async def test_continuous():
    """Test mode: Continuous monitoring."""
    print("\n" + "="*70)
    print("           CONTINUOUS MONITORING MODE")
    print("="*70)
    print("\nPress Ctrl+C to stop\n")
    
    central = BLE_UART_Central()
    visualizer = IMUVisualizer()
    ready_event = asyncio.Event()
    
    def on_receive(data_bytes: bytes):
        try:
            text = data_bytes.decode('utf-8')
        except Exception:
            return
        
        if isinstance(text, str) and text.strip().lower() == 'ready':
            ready_event.set()
            return
        
        try:
            data = json.loads(text)
            visualizer.update(data)
        except Exception:
            pass
    
    central.on_receive(on_receive)
    
    print("Connecting to databot...")
    if not await central.connect():
        print("❌ Failed to connect")
        return
    
    await central.send('Start')
    
    try:
        await asyncio.wait_for(ready_event.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pass
    
    print("✓ Connected\n")
    
    last_display = 0
    mode = 0  # Alternate between raw and orientation
    
    try:
        while True:
            await asyncio.sleep(0.1)
            
            if time.time() - last_display > 2.0:  # Switch every 2 seconds
                import os
                os.system('clear' if os.name != 'nt' else 'cls')
                
                if mode == 0:
                    visualizer.display_raw()
                    mode = 1
                else:
                    visualizer.display_orientation()
                    mode = 0
                
                last_display = time.time()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
    
    finally:
        if central.is_connected:
            await central.disconnect()
        
        visualizer.display_statistics()

# ---------------- Main Menu ----------------
def main():
    """Main test menu."""
    print("\n" + "="*70)
    print("           🧭 DATABOT IMU TEST TOOL")
    print("="*70)
    print("\nSelect test mode:")
    print("\n1. Raw IMU Data (accelerometer + gyroscope)")
    print("2. Orientation (pitch, roll, yaw, incline)")
    print("3. Continuous Monitoring (alternating display)")
    print("4. Exit")
    print("\n" + "-"*70)
    
    choice = input("\nSelect option [1-4]: ").strip()
    
    if choice == "1":
        duration = input("Duration (seconds, default 10): ").strip()
        duration = int(duration) if duration else 10
        asyncio.run(test_raw_imu(duration))
    
    elif choice == "2":
        duration = input("Duration (seconds, default 10): ").strip()
        duration = int(duration) if duration else 10
        asyncio.run(test_orientation(duration))
    
    elif choice == "3":
        asyncio.run(test_continuous())
    
    elif choice == "4":
        print("\n👋 Exiting...")
        return
    
    else:
        print("❌ Invalid option")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")