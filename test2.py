from machine import I2C, Pin
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
print("I2C scan:", [hex(x) for x in i2c.scan()])
