#
# Copyright (C) 2015-2016 Ettore Landini
#
# This code is translated from another project of mines written in C#
#
# This is a python library for the NewPort Agilis controller agUC2 and agUC8
#
# You can find another approach to this problem here: http://nullege.com/codes/show/src@t@e@terapy-2.00b6
#
#

from time import sleep

RATE = 750
LIMSPEED = 3
TIMEOUT = 2000 

## This class represente the real world axis of the agilis controller
class Axis(object):
    ## Class constructor
    # @param name The axis identifier for the serial port commands. It must be '1' or '2'
    # @param stepAmp The amplitude of each step taken by the motor. It can go from 0 to 50
    # @param rate The length in milliseconds of the interval between two consecutive checks of the motor state during a movement
    # @param controller The controller object that controls the axis
    def __init__(self,name = '1',stepAmp = 50,rate = RATE,controller = None):
        if controller == None:
            raise(ValueError('You cannot initialize an Axis without a controller'))
        self.controller = controller
        self.name = name
        self.rate = rate
        self.stepAmp = str(stepAmp) if 0<int(stepAmp)<=50 else str(50)
        self.controller.port.sendString(name+'SU+'+self.stepAmp)
        self.controller.port.sendString(name+'SU-'+self.stepAmp)
        
        self.__lastOp__ = 'opened'
    
    ## Returns the last operation executed by the axis
    def whatDidIdo(self):
        return self.__lastOp__
    
    ## Stops the axis
    def stop(self):
        self.controller.port.sendString(self.name+'ST')
        self.__lastOp__ = 'stopped'
    
    ## Check every "rate" milliseconds whether the motor is still or not
    # @param rate The length in milliseconds of the interval between two consecutive checks of the motor state during a movement
    def amIstill(self,rate):
        while True:
            if self.controller.port.sendString(self.name+'TS').find(b'0') != -1:
                return True
            sleep(0.001*rate)
            
    ## Check whether the motor's limit switch is on or not
    def amIatMyLimit(self):
        return self.controller.port.sendString('PH').find(self.name.encode()) != -1 or self.controller.port.sendString('PH').find(b'3') != -1
        
    ## Returns the number of accumulated steps in forward direction minus the number of steps in backward direction since powering the controller or since the last counter reset
    def queryCounter(self):
        return int(self.controller.port.sendString(self.name+'TP')[3:])
    
    ## Reset the step counter for the axis
    def resetCounter(self):
        self.controller.port.sendString(self.name+'ZP')
        self.__lastOp__ = 'reset'
        
    ## Takes "steps" steps in the direction specified by the sign of the "steps parameter"
    # @param steps The number of steps that have to be taken. + Positive direction - Negative direction
    def move(self,steps = 0):
        if steps == 0:
            return False
        self.__lastOp__ = 'moved: '+str(steps)
        self.controller.port.sendString(self.name+'PR'+str(int(steps)))

    def jog(self, mode=0):
        '''
        1 — Positive direction, 5 steps/s at defined step amplitude.
        2 — Positive direction, 100 steps/s at max. step amplitude.
        3 — Positive direction, 1700 steps/s at max. step amplitude.
        4 — Positive direction, 666 steps/s at defined step amplitude..
        '''
        self.__lastOp__ = 'joggd'
        self.controller.port.sendString(self.name+'JA'+str(mode))
    
    def goMax(self,speedTag = LIMSPEED):
        if self.__lastOp__ == 'goneMax':
            return False
        else:
            self.move(10)
            self.amIstill(100)
        self.__lastOp__ = 'goneMax'
        self.controller.port.sendString(self.name+'MV'+str(speedTag))
    
    def goMin(self,speedTag = LIMSPEED):
        if self.__lastOp__ == 'goneMin':
            return False
        else:
            self.move(-10)
            self.amIstill(100)            
        self.__lastOp__ = 'goneMin'
        self.controller.port.sendString(self.name+'MV'+str(-1*speedTag))

    def stepsPerRange(self, direction):
        #left to right 1, R2L -1
        self.controller.port.sendString(self.name+'MV'+str(direction*-3))
        self.amIstill(1000)
        print('---Start')
        self.resetCounter()
        self.move(direction * 100)
        self.amIstill(100)
        self.controller.port.sendString(self.name+'MV'+str(direction*4))
        self.amIstill(1000)
        count = self.queryCounter()
        print('---Finish')
        return count
        