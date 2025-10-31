# python
import serial
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation

class DatabotSerialTracker:
    def __init__(self, port="/dev/ttyACM0", baudrate=115200, update_rate=0.05):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # allow connection to stabilize
        self.dt = update_rate
        self.x = self.y = self.vx = self.vy = 0.0
        self.path_x, self.path_y = [0.0], [0.0]

    def read_imu_data(self):
        """Read IMU data line from Databot and parse acceleration (ax, ay, az)."""
        line = self.ser.readline().decode().strip()
        if not line:
            return 0, 0, 0

        # Expected format: "AX:0.02, AY:0.03, AZ:0.98"
        try:
            parts = line.replace(" ", "").split(",")
            ax = float(parts[0].split(":")[1])
            ay = float(parts[1].split(":")[1])
            az = float(parts[2].split(":")[1])
            return ax, ay, az
        except Exception:
            return 0, 0, 0

    def update_position(self):
        """Integrate acceleration to estimate 2D position."""
        ax, ay, _ = self.read_imu_data()
        ax *= 9.81
        ay *= 9.81
        self.vx += ax * self.dt
        self.vy += ay * self.dt
        self.x += self.vx * self.dt
        self.y += self.vy * self.dt
        self.path_x.append(self.x)
        self.path_y.append(self.y)

    def animate(self, i):
        self.update_position()
        line.set_data(self.path_x, self.path_y)
        return line,

    def live_plot(self, duration=10):
        """Show live 2D motion map."""
        fig, ax = plt.subplots()
        ax.set_title("Databot 2D Motion Tracker (USB Serial)")
        ax.set_xlabel("X Position (m)")
        ax.set_ylabel("Y Position (m)")
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        global line
        (line,) = ax.plot([], [], "bo-", markersize=5)

        ani = animation.FuncAnimation(fig, self.animate, interval=self.dt * 1000)
        plt.show()

# Example usage:
if __name__ == "__main__":
    tracker = DatabotSerialTracker(port="/dev/ttyUSB0")  # change if needed
    tracker.live_plot()
