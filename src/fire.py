import is31
from machine import SoftI2C, Pin
import time

i2c = SoftI2C(scl=Pin(1), sda=Pin(0))
display = is31.Matrix(i2c)

w, h = 7, 15
frame_delay = 0.015

f = open("anim.bin", "rb")

def read_byte():
    b = f.read(1)
    if not b:
        f.seek(0)
        b = f.read(1)
    return b[0]


while True:
    a = read_byte()
    if a >= 0x90:
        f.seek(0)
        a = read_byte()
    x1, y1 = a >> 4, a & 0x0F
    a = read_byte()
    x2, y2 = a >> 4, a & 0x0F
    
    for y in range(h):
        for x in range(w):
            if (x1 <= x <= x2) and (y1 <= y <= y2):
                color = read_byte()
            else:
                color = 0
            new_y = h - 1 - y
            new_x = x
            
            display.pixel(new_y + 1, new_x + 1, color)
            
    time.sleep(frame_delay)
