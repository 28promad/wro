# 🎨 Visual Guide - Dashboard Features

## Dashboard Screenshot (ASCII Art)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  🤖 Databot Rover Live Dashboard                            │
│                                                                             │
│  🟢 Connected  •  Last update: 10:15:05 AM  •  Data points: 1,437        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐   │
│  │ CO₂ Level          │  │ Humidity           │  │ Temperature        │   │
│  │ 419.9 ppm          │  │ 31.0 %             │  │ 28.3 °C            │   │
│  │ ✓ Good             │  │ ✓ Good             │  │ ⚠ Poor             │   │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘   │
│  ┌────────────────────┐                                                   │
│  │ TVOC               │                                                   │
│  │ 2.4 ppb            │                                                   │
│  │ ✓ Excellent        │                                                   │
│  └────────────────────┘                                                   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Environmental Sensors              IMU Acceleration                      │
│  ┌─────────────────────┐            ┌─────────────────────┐              │
│  │ CO₂ ╭─╮             │            │ AX ╱─╲              │              │
│  │     ╰─╮             │            │    ╭─╮ AY           │              │
│  │ TVOC  ─╯─╭─        │            │ AZ ╰───╯             │              │
│  │ TEMP   ╰─╯          │            │                     │              │
│  │ HUM              ╭─ │            │                     │              │
│  └─────────────────────┘            └─────────────────────┘              │
│                                                                             │
│  IMU Gyroscope                      2D Position (XY Map)                  │
│  ┌─────────────────────┐            ┌─────────────────────┐              │
│  │ GX ╱╲              │            │ Y  ╭─▶ Rover        │              │
│  │    ╰─╰─╮ GY        │            │    │    Path        │              │
│  │ GZ ─╭╮  ╰─╯        │            │    ├─▶              │              │
│  │     ╰─              │            │    └──▶            │              │
│  │                     │            │             X→     │              │
│  └─────────────────────┘            └─────────────────────┘              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Rover Kinematics & Position                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ Position X   │  │ Position Y   │  │ Heading (Yaw)│                   │
│  │ 1.234 m      │  │ 0.567 m      │  │ 45.2 °       │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Status Indicators

### Connection Status
```
🟢 Connected        - Databot is connected, data flowing
🔴 Disconnected     - Databot not connected, local sensors only
⚪ Connecting       - Attempting to connect (brief)
```

### Sensor Status (Color-Coded)

```
✓ Good          - Value is within safe range (green border)
⚠ Warning       - Value is approaching threshold (orange border)
⚠ Danger        - Value exceeds safe limits (red border)
```

## Threshold Values

### Environmental Sensors

```
CO₂ Level:
  Good:    < 1000 ppm
  Warning: 1000-2000 ppm
  Danger:  > 2000 ppm

TVOC:
  Good:    < 400 ppb
  Warning: 400-800 ppb
  Danger:  > 800 ppb

Temperature:
  Good:    < 30 °C
  Warning: 30-40 °C
  Danger:  > 40 °C

Humidity:
  Good:    30-70 %
  Warning: Outside range
```

## Chart Types

### 1. Environmental Sensors Chart
```
Type: Line Chart (dual-axis)
Left Axis:   CO₂, TVOC (ppm/ppb)
Right Axis:  Temp (°C), Humidity (%)
Lines:       4 colored lines for each sensor
Update:      Real-time (50ms typical)
History:     Last 100 readings (~100 seconds)
```

### 2. IMU Acceleration Chart
```
Type: Line Chart
Axis:        m/s² (meters per second squared)
Lines:       3 colored lines (AX, AY, AZ)
Update:      Real-time (50ms typical)
History:     Last 100 readings (~2 seconds at 50Hz)
Use:         Monitor physical acceleration/vibration
```

### 3. IMU Gyroscope Chart
```
Type: Line Chart
Axis:        rad/s (radians per second)
Lines:       3 colored lines (GX, GY, GZ)
Update:      Real-time (50ms typical)
History:     Last 100 readings (~2 seconds)
Use:         Monitor rotational rates/turns
```

### 4. 2D Position Chart
```
Type: Scatter with line connection
Axis X:      Position X (meters)
Axis Y:      Position Y (meters)
Data:        Rover's actual position on 2D map
Update:      Real-time (50ms typical)
History:     Last 100 readings
Use:         Visualize rover's path through tunnel
```

## Color Scheme

### Chart Colors

```
CO₂:         #FF6B6B  (Red)
VOC/TVOC:    #4ECDC4  (Cyan)
Temperature: #FFE66D  (Yellow)
Humidity:    #95E1D3  (Light Green)

AX:          #A8E6CF  (Mint)
AY:          #FFD3B6  (Peach)
AZ:          #FFAAA5  (Pink)

GX:          #67B7DC  (Blue)
GY:          #C8B6E2  (Lavender)
GZ:          #FFB6C1  (Rose)
```

### UI Colors

```
Primary:     #00d4ff  (Cyan - headers, borders)
Success:     #00ff99  (Green - good status)
Warning:     #ff8800  (Orange - warnings)
Danger:      #ff4444  (Red - errors)
Background:  #0d1b2a  (Dark navy)
Text:        #e0e0e0  (Light gray)
```

## Real-Time Update Visualization

### WebSocket Mode (Recommended)

```
Timeline:
────────────────────────────────────────────────
T=0ms    : Sensor reading acquired
T=1ms    : Data service updated
T=5ms    : WebSocket broadcast
T=20ms   : Browser receives
T=25ms   : Chart updates
────────────────────────────────────────────────
Total: ~25ms latency ✨ Smooth!
```

### Polling Mode (Fallback)

```
Timeline:
────────────────────────────────────────────────
T=0s     : Dashboard polls API
T=10ms   : API response
T=20ms   : Data received
T=100ms  : Chart updates
T=2000ms : Next poll
────────────────────────────────────────────────
Total: ~2000ms (2 second) latency
Update frequency: Every 2 seconds
```

## Sensor Card Layout

```
┌─────────────────────────────┐
│ CO₂ LEVEL (uppercase title) │
│                             │
│ 419.9 ppm (large value)    │
│                             │
│ ✓ Good (status indicator)  │
└─────────────────────────────┘
```

### Status Indicators

```
✓ Good     - Green text, good condition
⚠ Warning  - Orange text, borderline
⚠ Danger   - Red text, alert condition
–– No data - Gray text, not connected
```

## Mobile Responsiveness

### Desktop View
```
4 columns of sensor cards
2x2 grid of charts
Position section at bottom
All labels visible
```

### Tablet View
```
2-3 columns of sensor cards
1 chart per row
Position section flexible
Some labels abbreviated
```

### Mobile View
```
1 column of sensor cards (full width)
1 chart per row (full width)
Position section single column
Compact display
Swipe-friendly
```

## Real-Time Features

### Auto-Update Indicators

```
Last Update: 10:15:05 AM
Data Points: 1,437

These update automatically as new data arrives.
```

### Connection Status

```
🟢 Connected    - Live feed active
🔴 Disconnected - Last known values shown
```

### Thresholds & Alerts

```
Cards highlight when thresholds crossed:

Green border  - All good ✓
Orange border - Getting close ⚠
Red border    - Alert state ⚠
```

## Data Resolution

```
Sensor            Rate      Resolution
─────────────────────────────────────
IMU (Accel/Gyro)  50 Hz     ±6 decimal places
Environmental     1 Hz      1 decimal place
Timestamp         1 Hz      ISO 8601 format
Position          50 Hz     ±6 decimal places
Heading           50 Hz     ±1 decimal place
```

## Example Real-Time Sequence

```
Second 1:
  CO₂: 419.9 → 420.1 ppm (updating...)
  Temp: 28.3 → 28.2 °C (cooling)
  Position: X: 1.234 → 1.245 m (moving forward)

Second 2:
  Humidity: 31.0 → 30.8 % (changing)
  All graphs shift left, new data added
  
Second 3:
  TVOC: 2.4 → 2.3 ppb (nominal)
  Charts animate smoothly
  Position plot extends path line
```

## Responsive Layout Breakpoints

```
Desktop (> 1200px)
├─ 2 charts per row
├─ 4 sensor cards per row
└─ Full feature set

Tablet (768px - 1200px)
├─ 1 chart per row
├─ 2-3 sensor cards per row
└─ Optimized spacing

Mobile (< 768px)
├─ 1 chart per row (full width)
├─ 1 sensor card per row (full width)
└─ Vertical layout
```

## Interactive Features

### Hover Effects
```
Sensor Cards:
  - Lift up slightly
  - Shadow deepens
  - Border brightens

Charts:
  - Cursor changes to crosshair
  - Tooltip shows values
  - Legend highlights on hover
```

### Click Interactions
```
Status Indicator:
  - Shows connection details on click
  
Charts:
  - Dataset legend toggles visibility
  - Right-click shows save options
  
Refresh:
  - Manual data request
  - Auto-refresh via WebSocket
```

## Legend

### Chart Legend Example

```
Chart Legend (Click to toggle):
✓ CO₂         ✓ TVOC
✓ Temperature ✓ Humidity

Clicking any item hides/shows that line
```

---

This visual guide helps you understand what you'll see when the dashboard loads!
