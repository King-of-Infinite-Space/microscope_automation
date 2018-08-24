#!/usr/bin/python
# Filename: InstrumentControl.py


#serial is a modified python serial module which disables the dtrState preventing
#resets when the serial session is closed.
#http://www.arduino.cc/cgi-bin/yabb2/YaBB.pl?num=1274205532

#Code adapted from Dan Thompson and build-in Arduino examples
#http://danthompsonsblog.blogspot.com/2009/04/python-arduino-motor-shield-stepper.html
#and
#http://danthompsonsblog.blogspot.com/2008/09/easydriver-v31-tutorial.html

import serial
import time

def help():
	print('InstrumentControl.py currently supports:')
	print('Stepper Motor Control')

endChar = '>'

def encodeMessage(message):
    return (str(message) + endChar).encode()

class StepperMotor:
    def __init__(self, StepperMotorAddress):
        self.StepperMotorAddress = StepperMotorAddress
        self.StepperMotor = serial.Serial(StepperMotorAddress, 115200, timeout=0.25)
        print("----StepperMotor: Serial Communication Open") 
        time.sleep(1)
        
    def CloseSerial(self):
        #Close Serial Port
        self.StepperMotor.close()
        print("----StepperMotor: Serial Communication Closed")  
        return

    def Step(self, steps):
        # turns the knob clockwise
        self.StepperMotor.write(encodeMessage(steps))
        if steps > 100:
            timeToWait = steps / 1000
        else:
            timeToWait = 0.05
        time.sleep(timeToWait) # this seems important to reduce lag or prevent getting stuck
        
    def GetPosition(self):
        self.StepperMotor.reset_input_buffer()
        self.StepperMotor.write(encodeMessage(987))
        time.sleep(0.05)
        StepperPosition=self.StepperMotor.readline().decode()[:-2]
        return int(StepperPosition)
        
    '''    
    def SetPosition(self,num,degsPerStepFloat,stepsFloat):
       steps = int(stepsFloat / degsPerStepFloat)
       if(steps < 65535 and steps > -1):
               binary = DecimalToBinary(steps)
               numBytes = BinaryCount(binary)
               self.StepperMotor.write(chr(255))
               # ascii character
               #Note: The 2 in (0,2,1) allows for the transmission of two bytes.
               for i in range(0,2,1):
                       sBinary = str(binary)
                       firstByte = int(sBinary,2) & int('11111111',2)
                       newBinary = int(sBinary,2) >> 8
                       binary = DecimalToBinary(newBinary)
                       self.StepperMotor.write(chr(firstByte))
       if(steps > -65535 and steps < 0):
               stepsNeg = steps * -1
               binary = DecimalToBinary(stepsNeg)
               numBytes = BinaryCount(binary)
               self.StepperMotor.write(chr(220))
               #Note: The 2 in (0,2,1) allows for the transmission of two bytes.
               for i in range(0,2,1):
                       sBinary = str(binary)
                       firstByte = int(sBinary,2) & int('11111111',2)
                       newBinary = int(sBinary,2) >> 8
                       binary = DecimalToBinary(newBinary)
                       self.StepperMotor.write(chr(firstByte))
       time.sleep(1)
       return stepsFloat
    
        
    def GetPosition(self):
        message = chr(5)+chr(0)+chr(0)
        self.StepperMotor.write(encodeMessage(message))
        time.sleep(1)
        StepperPosition=self.StepperMotor.readline()
        return StepperPosition
    def GetVersion(self):
        message = chr(118)+chr(0)+chr(0)
        self.StepperMotor.write(encodeMessage(message))
        time.sleep(1)
        FirmwareVersion=self.StepperMotor.readline()
        return FirmwareVersion
    '''

#Convert integer n (base 10) to a binary string (base 2)
def DecimalToBinary(n):
   if n < 0: raise ValueError("must be a positive integer")
   BinaryString=bin(n)[2:]
   return BinaryString

#Returns the number of bit bytes (eighths) in binary string. Rounds up.
def BinaryCount(number):
    sNumber = str(number)
    length = len(sNumber)
    numBytes = length / 8.0
    numBytesInt = length / 8
    if numBytes > numBytesInt:
        return numBytesInt + 1
    else:
        return numBytesInt

# End of InstrumentControl.py