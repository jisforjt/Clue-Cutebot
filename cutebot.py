# CircuitPython Clue Cutebot
# Last upDated July 23, 2020
# Author(s): James Tobin

######################################################
#   Cutebot Informatoin
######################################################
'''
cutebot.py:
    Is a higher level library written for use by young codeing learners using
    Adafruit's Clue and Elecfreaks Smart Cutebot. The code was written as simple
    as possible and redundent to support their educational needs.

TODO:
    ADD Cutebot P1 and P2 Sensor input (S 3V G)
    ADD Ultra sound sensor
    ADD Line Tracking sensors
    ADD Cutebot Infrared Control
'''

######################################################
#   Renference Informatoin
######################################################
"""
I2C Devices
    0x10 -Cutebot (i2c frequency = 100000)
    0x1c -LIS3MDL 3-axis magnetometer sensor
    0x39 -APDS9960 esture, proximity, and color sensor
    0x44 -SHT31-D temperature and humidity sensor
    0x6a -LSM6DS 6-axis accelerometer and gyro sensor
    0x77 -BMP280 temperature and barometic pressure sensor

Pins
    P0  -Digital    Cutebot Buzzer
    P1  -Analog     Cutebot P1 Sensor input (S 3V G)
    P2  -Analog     Cutebot P2 Sensor input (S 3V G)
    P5  -Digital    Clue Button A
    P8  -Digital    Cutebot ultrasonic pulse transmitter (2cm-400cm, precision +-1.5mm)
    P11 -Digital    Clue Button B
    P12 -Digital    Cutebot ultrasonic pulse reciever
    P13 -Digital    Cutebot left line tracking
    P14 -Digital    Cutebot right line tracking
    P15 -Digital    Cutebot Neopixel
    P16 -Digital    Cutebot Infrared Control
    P17 -Digital    Clue LED
    P18 -Digital    Clue Neopixel
    P19 -Digital    Shared IIC Port G V P19 P20
    P20 -Digital    Shared IIC Port G V P19 P20
    P43 -Digital    Clue White LEDs

Motors
    Hex Data[0]
        0x01 Left Motor
        0x02 Right Motor
        0x04 RGB Right Headlight
        0x05 Servo 1 (S1)
        0x06 Servo 2 (S2)
        0x08 RGB Left Headlight

    Hex Data[1]
        0x01 motors backwards
        0x02 motors fowardwards
"""


######################################################
#   Import
######################################################
import time
import board
import busio
import pulseio
import neopixel
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
from cutebot_adafruit_clue import clue
import lib/adafruit_irremote
import lib/adafruit_hcsr04


######################################################
#   Set up pins
######################################################
rainbow_pixels = neopixel.NeoPixel(board.D15, 2)      #Set neopixel pin 

P1_sensor = AnalogIn(board.P1)      #Set P1 sensor pin

P2_sensor = AnalogIn(board.P2)      #Set P2 sensor pin

sonar = adafruit_hcsr04.HCSR04(trigger_pin=board.D8, echo_pin=board.D12)    #Set sonar sensor pins

leftLineTracking = DigitalInOut(board.D13)      #Set left line tracking pin
leftLineTracking.direction = Direction.INPUT
leftLineTracking.pull = None

rightLineTracking = DigitalInOut(board.D14)     #Set right line tracking pin
rightLineTracking.direction = Direction.INPUT
rightLineTracking.pull = None

pulsein = pulseio.PulseIn(board.D16, maxlen=120, idle_state=True)       #Set Infrared (IR) pin

buzzer = pulseio.PWMOut(board.P0, variable_frequency=True)      #Set buzzer pin


######################################################
#   Set up I2C communications with Cutebot
######################################################
''' 
We will use a suggestion from https://forums.adafruit.com/viewtopic.php?f=60&t=165077.
Using a modified adafruit_clue file that was renamed to my_adafruit_clue and changing the way 
that that file estableshes the shared i2c connection, we can use clue._i2c to control Cutebot's
motors, servos, lights and sensors.
'''
cutebot_address = 0x10

######################################################
#   Global Variables
######################################################
servoMaxAngleInDegrees = 180    #Maximum degrees of freedom allowed by your servo (change to match your servo)
decoder = adafruit_irremote.GenericDecode()     #Set infrared (IR) decoder to Adafruit's generic decoder
i2c_rest = 0.1

######################################################
#   ----------------- FUNCTIONS -----------------
######################################################
'''
Sounds
    - buzzer()
Lights
    - headlights(whichLight, colors)
    - pixel(whichLight, colors)
    - lightsOff()
Motors
    - motors(leftSpeed, rightSpeed)
    - motorsOff()
Servos
    - servos(whichServo, angleInDegrees)
    - centerServos()
Sensors
    - getP1()       retruns one analog value
    - getP2()       returns one analog value
    - getSonar()    returns the distance in centimeters
    - getTracking() returns two boolean values
    - getIR()       returns decoded IR pattern
'''


######################################################
#   Sounds
######################################################
def playTone(tone, duration):
    '''
    tone =  the frequency of the tones/music notes you want to play
    duration = the number of seconds you want to hear the tone
     
        tone     music note
        262    =     C4
        294    =     D4
        330    =     E4
        349    =     F4
        392    =     G4
        440    =     A4
        494    =     B4

    examples:
        playTone(294, 0.5)
        playTone(349, 1.0)
        playTone(440, 2.2)
    '''
    buzzer.frequency = tone     #Set the tone 
    buzzer.duty_cycle = 2**15   #Turn sound ON
    time.sleep(duration)        #
    buzzer.duty_cycle = 0       #Turn sound OFF


######################################################
#   Lights
######################################################
def headlights(whichLight, colors):
    '''
    whichLight (integer):
        0 = Set both lights to off
        1 = Set left light only
        2 = Set right light only
        3 = Set both lights

    colors - RGB (array of three integers):
        colors[0] = red
        colors[1] = green
        colors[2] = blue

    examples:
        black = [0, 0, 0]
        white = [255, 255, 255]
        pink = [255, 192, 203]
        red = [255, 0, 0]
        headlights(0, black)          #Turns off the headlights
        headlights(1, pink)           #Sets the left headlight to pink
        headlights(2, red)            #Sets the right headlight to red
        headlights(3, [80, 255, 80])  #Sets both headlights to a light green color
    '''
    while not clue._i2c.try_lock():
        pass
    while True:
        try:
            data = [0,0,0,0]        #cuteBot expects four bytes of data
            red, green, blue = colors
            r = min(max(red, 0),255)    #let's make sure that the red color is between 0 and 255
            g = min(max(green, 0),255)  #let's make sure that the green color is between 0 and 255
            b = min(max(blue, 0),255)   #let's make sure that the blue color is between 0 and 255
            if whichLight == 0:     #SET BOTH LIGHTS OFF
                data[0] = 0x08      #left (0x08) or right (0x04) light
                data[1] = 0         #red
                data[2] = 0         #green
                data[3] = 0         #blue
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
                data[0] = 0x04      #left (0x08) or right (0x04) light
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            elif whichLight == 1:   #SET LEFT LIGHT ONLY
                data[0] = 0x04      #left (0x08) or right (0x04) light
                data[1] = r         #red
                data[2] = g         #green
                data[3] = b         #blue
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            elif whichLight == 2:   #SET RIGHT LIGHT ONLY
                data[0] = 0x08      #left (0x08) or right (0x04) light
                data[1] = r         #red
                data[2] = g         #green
                data[3] = b         #blue
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            elif whichLight == 3:   #SET BOTH LIGHTS
                data[0] = 0x08      #left (0x08) or right (0x04) light
                data[1] = r         #red
                data[2] = g         #green
                data[3] = b         #blue
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
                data[0] = 0x04      #left (0x08) or right (0x04) light
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            else:
                print("whichLight should be a 0, 1, 2, or 3.")
            break
        except:
            print('headlights i2c Error')
            pass
    clue._i2c.unlock()
    time.sleep(i2c_rest)

def pixels(whichLight, colors):
    '''
    whichLight (integer):
        0 = Set both lights to off
        1 = Set left light only
        2 = Set right light only
        3 = Set both lights

    colors - RGB (array of three integers):
        colors[0] = red
        colors[1] = green
        colors[2] = blue
        colors[3] = white or brightness

    examples:
        black = [0, 0, 0, 0]
        white = [255, 255, 255, 255]
        pink = [255, 192, 203, 255]
        red = [255, 0, 0, 255]
        headlights(0, black)          #Turns off the headlights
        headlights(1, pink)           #Sets the left headlight to pink
        headlights(2, red)            #Sets the right headlight to red
        headlights(3, [80, 255, 80, 200])  #Sets both headlights to a light green color
    '''
    red, green, blue = colors
    r = min(max(red, 0),255)    #let's make sure that the red color is between 0 and 255
    g = min(max(green, 0),255)  #let's make sure that the green color is between 0 and 255
    b = min(max(blue, 0),255)   #let's make sure that the blue color is between 0 and 255
    if whichLight == 0:       #SET BOTH LIGHTS OFF
        rainbow_pixels[0] = (0, 0, 0)               #Set left light
        rainbow_pixels[1] = (0, 0, 0)               #Set right light
    elif whichLight == 1:     #SET LEFT LIGHT ONLY
        rainbow_pixels[0] = (r, g, b)               #Set left light
    elif whichLight == 2:     #SET RIGHT LIGHT ONLY
        rainbow_pixels[1] = (r, g, b)               #Set right light
    elif whichLight == 3:     #SET BOTH LIGHTS 
        rainbow_pixels[0] = (r, g, b)               #Set left light
        rainbow_pixels[1] = (r, g, b)               #Set right light
    else:
        print("whichLight should be a 0, 1, 2, or 3.")

def lightsOff():
    headlights(0,[0,0,0])   #Turns off the headlights
    pixels(0, [0,0,0])    #Turns off the pixels


######################################################
#   Motors
######################################################
def motors(leftSpeed, rightSpeed):      #Set motors speeds
    '''
    leftSpeed = the speed of the left motor (integer between -100 and 100)
    rightSpeed = the speed of the right motor (integer between -100 and 100)

    examples:
        motors(50, 20)      #sets cutebot's motors so it turns right slowly
        motors(-100, 100)   #sets cutebot's motors so it spins counter-clockwise
        motors(-50, -50)    #sets cutebot's motors so it backs up at about half speed
    '''
    while not clue._i2c.try_lock():
        pass
    while True:
        try:
            leftSpeed = min(max(leftSpeed, -100),100)   #let's make sure the value is between -100 and 100
            rightSpeed = min(max(rightSpeed, -100),100) #let's make sure the value is between -100 and 100
            data = [0,0,0,0]        #cuteBot expects four bytes of data and the last one is always zero when sending motor data
            if leftSpeed == 0 and rightSpeed == 0:
                data[0] = 0x01          #left (0x01) or right (0x02) motor
                data[1] = 0x02          #forwards (0x02) or backwards (0x01)
                data[2] = 0             #speed
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
                data[0] = 0x02          #left (0x01) or right (0x02) motor
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            if leftSpeed > 0:
                data[0] = 0x01          #left (0x01) or right (0x02) motor
                data[1] = 0x02          #forwards (0x02) or backwards (0x01)
                data[2] = leftSpeed     #speed
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            else:
                data[0] = 0x01              #left (0x01) or right (0x02) motor
                data[1] = 0x01              #forwards (0x02) or backwards (0x01)
                data[2] = leftSpeed * -1    #speed (We multiply by -1 to make the value positive. Cutebot accually wants a value between 0 and 100)
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            if rightSpeed > 0:
                data[0] = 0x02          #left (0x01) or right (0x02) motor
                data[1] = 0x02          #forwards (0x02) or backwards (0x01)
                data[2] = rightSpeed    #speed
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            else:
                data[0] = 0x02              #left (0x01) or right (0x02) motor
                data[1] = 0x01              #forwards (0x02) or backwards (0x01)
                data[2] = rightSpeed * -1   #speed (We multiply by -1 to make the value positive. Cutebot accually wants a value between 0 and 100)
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            break
        except:
            print('Motor i2c ERROR')
            pass
    clue._i2c.unlock()
    time.sleep(i2c_rest)

def motorsOff():
    motors(0,0)     #Stop motors


######################################################
#   Servos
######################################################
def servos(whichServo, angleInDegrees):     #set servos angles
    '''
    whichServo:
        1 = S1 Servo (0x05)
        2 = S2 Servo (0x06)
        3 = S1 and S2

    examples:
        servos(1, 90)       #Sets Servo S1 to 90 degrees
        servos(2, 120)      #Sets Servo S2 to 120 degrees
        servos(3, 180)      #Sets Servo S1 and S2 to 180 degrees
    '''
    while not clue._i2c.try_lock():
        pass
    while True:
        try:
            data = [0,0,0,0]        #cuteBot expects four bytes and the last two are always zero when sending servo data
            angleInDegrees = min(max(angleInDegrees, 0),servoMaxAngleInDegrees)     #let's make sure that our angle is between 0 and servoMaxAngleInDegrees
            if whichServo == 1:             #SET SERVO S1
                data[0] = 0x05              #S1 Servo (0x05) and S2 Servo (0x06)
                data[1] = angleInDegrees    #servo new angle
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            elif whichServo == 2:           #SET SERVO S2
                data[0] = 0x06              #S1 Servo (0x05) and S2 Servo (0x06)
                data[1] = angleInDegrees    #servo new angle
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            else:                           #SET SERVO S1 & S2
                data[0] = 0x05              #S1 Servo (0x05) and S2 Servo (0x06)
                data[1] = angleInDegrees    #servo new angle
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
                data[0] = 0x06              #S1 Servo (0x05) and S2 Servo (0x06)
                clue._i2c.writeto(cutebot_address, bytes(data))     #Send data to cutebot
            break
        except:
            print('Servo i2c ERROR')
            pass
    clue._i2c.unlock()
    time.sleep(i2c_rest)
def centerServos():     #set both servo arms to the center
    servos(3,(servoMaxAngleInDegrees/2))


######################################################
#   Sensors
######################################################
def getP1():
    return P1_sensor.value

def getP2():
    return P2_sensor.value

def getSonar():
    '''
    Output: the distance in centimeters between the cutebot and an object in front of it
    '''
    data = []
    while len(data) < 3:
        try:
            data.append(sonar.distance)
        except RuntimeError:
            #print("ERROR: Sonar Runtime")
            pass
        time.sleep(0.025)
    distance = sum(data) - min(data) - max(data)
    return round(distance, 2)

def getTracking():
    '''
    Output: left driver side sensor, right driver side sensor

    True = I see black
    False = I see white
    '''
    return not leftLineTracking.value, not rightLineTracking.value

def getIR():
    pulses = decoder.read_pulses(pulsein)
    try:
        # Attempt to convert received pulses into numbers
        received_code = decoder.decode_bits(pulses, debug=False)
    except adafruit_irremote.IRNECRepeatException:
        # We got an unusual short code, probably a 'repeat' signal
        # print("NEC repeat!")
        pass
    except adafruit_irremote.IRDecodeException as e:
        # Something got distorted or maybe its not an NEC-type remote?
        # print("Failed to decode: ", e.args)
        pass
    return received_code

motorsOff()
lightsOff()
print('======== Cutebot Loaded ========')