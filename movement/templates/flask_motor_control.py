# python
import time
from flask import Flask, render_template_string
import RPi.GPIO as GPIO

# GPIO setup
in1, in2, en_a = 17, 27, 18
in3, in4, en_b = 5, 6, 13
GPIO.setmode(GPIO.BCM)
GPIO.setup([in1, in2, en_a, in3, in4, en_b], GPIO.OUT)

right_pwm = GPIO.PWM(en_a, 100)
left_pwm  = GPIO.PWM(en_b, 100)
right_pwm.start(50)
left_pwm.start(50)

# --- Movement functions ---
def stop():
    GPIO.output([in1, in2, in3, in4], GPIO.LOW)

def move_forward():
    GPIO.output(in1, GPIO.HIGH)
    GPIO.output(in4, GPIO.HIGH)
    GPIO.output(in2, GPIO.LOW)
    GPIO.output(in3, GPIO.LOW)

def move_backward():
    GPIO.output(in2, GPIO.HIGH)
    GPIO.output(in3, GPIO.HIGH)
    GPIO.output(in1, GPIO.LOW)
    GPIO.output(in4, GPIO.LOW)

def move_left():
    GPIO.output(in1, GPIO.HIGH)
    GPIO.output(in3, GPIO.HIGH)
    GPIO.output(in2, GPIO.LOW)
    GPIO.output(in4, GPIO.LOW)

def move_right():
    GPIO.output(in2, GPIO.HIGH)
    GPIO.output(in4, GPIO.HIGH)
    GPIO.output(in1, GPIO.LOW)
    GPIO.output(in3, GPIO.LOW)


# --- Flask Web App ---
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Rover Control Panel</title>
  <style>
    body { font-family: sans-serif; text-align: center; background: #111; color: white; }
    h1 { margin-top: 20px; }
    button {
      background: #333; color: white; border: none; border-radius: 10px;
      padding: 20px; margin: 10px; font-size: 20px; width: 100px; height: 100px;
      transition: background 0.2s;
    }
    button:active { background: #0f0; color: black; }
    .controls { display: flex; flex-direction: column; align-items: center; margin-top: 40px; }
    .row { display: flex; justify-content: center; }
  </style>
</head>
<body>
  <h1>🚗 Rover Control</h1>
  <p>Use <strong>W / A / S / D</strong> keys or buttons below to control.<br>Release to stop.</p>

  <div class="controls">
    <div class="row">
      <button onmousedown="move('forward')" onmouseup="move('stop')">↑</button>
    </div>
    <div class="row">
      <button onmousedown="move('left')" onmouseup="move('stop')">←</button>
      <button onmousedown="move('backward')" onmouseup="move('stop')">↓</button>
      <button onmousedown="move('right')" onmouseup="move('stop')">→</button>
    </div>
  </div>

  <script>
    function move(cmd) { fetch('/move/' + cmd); }

    document.addEventListener('keydown', e => {
      const key = e.key.toLowerCase();
      if (['w','a','s','d'].includes(key)) {
        fetch('/move/' + ({'w':'forward','a':'left','s':'backward','d':'right'}[key]));
      }
    });
    document.addEventListener('keyup', e => fetch('/move/stop'));
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/move/<cmd>')
def move(cmd):
    commands = {
        'forward': move_forward,
        'backward': move_backward,
        'left': move_left,
        'right': move_right,
        'stop': stop
    }
    if cmd in commands:
        commands[cmd]()
    return ('', 204)

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8000, threaded=True)
    finally:
        stop()
        GPIO.cleanup()
