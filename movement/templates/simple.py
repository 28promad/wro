# python
from gpiozero import Motor, PWMOutputDevice
from time import sleep


# Right motor
right_motor = Motor(forward=20, backward=16, pwm=True)
right_enable = PWMOutputDevice(21)

# Left motor
left_motor = Motor(forward=12, backward=13, pwm=True)
left_enable = PWMOutputDevice(7)

# Start both motors at 45% duty
right_enable.value = 0.2
left_enable.value = 0.2

def set_speed(level):
    duty = level / 100
    right_enable.value = duty
    left_enable.value = duty
    print(f"Speed: {level}%")

def stop_all():
    right_motor.stop()
    left_motor.stop()

try:
    while True:
        user_input = input()

        # Speed control
        if user_input in '123456789':
            set_speed(int(user_input) * 10)

        elif user_input == 'w':
            right_motor.forward()
            left_motor.forward()
            print("Forward")

        elif user_input == 's':
            right_motor.backward()
            left_motor.backward()
            print("Back")

        elif user_input == 'd':
            # turn right: left forward, right stop/backward
            right_motor.backward()
            left_motor.stop()
            print("Right")

        elif user_input == 'a':
            # turn left: right forward, left stop/backward
            left_motor.backward()
            right_motor.stop()
            print("Left")

        elif user_input == 'r':
            # 180 turn: opposite directions
            right_motor.forward()
            left_motor.backward()
            sleep(2)
            stop_all()
            print("180 Degree Turn")

        elif user_input == 't':
            # 180 turn: opposite directions
            right_motor.backward()
            left_motor.forward()
            sleep(2)
            stop_all()
            print("180 Degree Turn")


        elif user_input == 'c':
            stop_all()
            print("Stop")

except KeyboardInterrupt:
    stop_all()
    print("GPIO Clean up")
