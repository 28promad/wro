# WRO Databot Project

A comprehensive robotics project combining a Raspberry Pi and ESP32-based Databot for environmental monitoring and autonomous navigation.

## Overview

This project consists of two main components:
1. **Databot** (ESP32-based): Environmental sensor hub with LED feedback
2. **Raspberry Pi**: Navigation control and motor management

## Hardware Components

### Databot (ESP32)
- SHTC3 Temperature & Humidity Sensor
- SGP30 Air Quality Sensor (CO2 and TVOC)
- WS2812C-2020 RGB LED Ring (3 LEDs)
- SMT-0540-T-2-R Buzzer
- APDS9960 Gesture/Color Sensor
- GUVA-S12SD UV Sensor
- External DS18B20 Temperature Probes

### Raspberry Pi
- Motor Control System
- Ultrasonic Distance Sensors
  - Front (TRIG: 23, ECHO: 24)
  - Left (TRIG: 25, ECHO: 8)
  - Right (TRIG: 7, ECHO: 12)
- Motors:
  - Right Motor: IN1(17), IN2(27), EN_A(4)
  - Left Motor: IN3(5), IN4(6), EN_B(13)

## Software Structure

### Core Components
```
├── main_databot.py      # Main Databot control script
├── main_pi.py          # Main Raspberry Pi control script
├── comms/              # Communication modules
│   ├── serial_databot.py
│   └── serial_pi.py
├── databot/            # Databot core functionality
│   └── databoot.py
└── movement/           # Motor control and navigation
    └── motor_controller.py
```

### Sensors and Features
```
sensors/
└── databot/
    ├── buzzer.py      # Audio feedback
    ├── ext_temperature.py
    ├── led.py         # Visual feedback
    ├── sgp30.py       # Air quality
    └── shtc3.py       # Temperature/Humidity
```

## Setup and Installation

1. **Databot Setup**
   ```bash
   # Flash ESP32 with MicroPython
   # Upload the following files to ESP32:
   - databot/databoot.py
   - main_databot.py
   - comms/serial_databot.py
   - sensors/databot/*
   ```

2. **Raspberry Pi Setup**
   ```bash
   # Install required Python packages
   pip install pyserial RPi.GPIO

   # Connect hardware:
   - Connect motors to specified GPIO pins
   - Connect ultrasonic sensors
   - Connect Databot via USB
   ```

## Usage

1. **Start the System**
   ```bash
   # On Raspberry Pi:
   python main_pi.py
   ```

   The system will:
   - Initialize serial communication
   - Set up motor controllers
   - Begin autonomous navigation
   - Monitor environmental data

2. **Test Communications**
   ```bash
   # Test Databot communication
   python test_comm_pi.py
   
   # Test motor controls
   python movement/motor_controller.py
   ```

## Environmental Monitoring

The Databot monitors:
- Temperature (°C)
- Relative Humidity (%)
- CO2 levels (ppm)
- TVOC levels (ppb)

### Alert Thresholds
- CO2: > 1000 ppm
- TVOC: > 400 ppb
- Temperature: > 30°C
- Humidity: < 30% or > 70%

## LED Indicators

Three RGB LEDs provide status feedback:
- LED 0: Air Quality (Green=Good, Red=Poor)
- LED 1: Temperature (Green=Normal, Red=High)
- LED 2: Humidity (Green=Normal, Red=Outside Range)

## Motor Control

The system supports:
- Forward/Backward movement
- Left/Right turns
- Speed control via PWM
- Obstacle avoidance using ultrasonic sensors

## Development

### Testing
```bash
# Test communication between Pi and Databot
python test_comm_pi.py
python test_comm_databot.py

# Test motor controls
python movement/motor_controller.py
```

### Movement Templates
The `movement/templates/` directory contains example implementations:
- `simple_motor_control.py`: Basic motor control
- `flask_motor_control.py`: Web-based control interface
- `simulation1.py`: Movement simulation

## License

This project is provided as-is for educational and experimental purposes.