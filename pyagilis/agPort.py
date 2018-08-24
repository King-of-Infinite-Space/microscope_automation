#
# Copyright (C) 2015-2016 Ettore Landini
#
# This code is translated from another project of mines written in C#
#
# This is a python library for the NewPort Agilis controlle agUC2 and agUC8
#
# You can find another approach to this problem here: http://nullege.com/codes/show/src@t@e@terapy-2.00b6
#

## @package agPort
# This module contain classes that implements custom versions of python built-in serial port class
# for the agilis controllers 
#

import serial
from datetime import datetime
from time import sleep

## Documentation for the AGPort class
#
# This class extend the python Serial class with some function that simplifies its use with the agilis controllers commands
class AGPort(serial.Serial):
    
    ## Class constructor
    # @param portName The name of the virtual serial port of the chosen controller
    def __init__(self,portName = None):    
        if portName == None:
            ## @var AGPort.soul
            self.soul = None
            return None
        try:
            super().__init__(portName,921600,serial.EIGHTBITS,serial.PARITY_NONE,serial.STOPBITS_ONE, timeout=1)
            self.soul = 'p'
            #self.input_buffer_log = []
            sleep(0.1)
        except Exception as e:
            print(e)
            print('I could not find or open the port you specified: {0}'.format(portName))
            self.soul = None
            return None
        

    ## Checks if the port has been successfully opened
    def amInull(self):
        return self.soul is None
    
    ## Checks whether the string you sent is supposed to get an answer or not
    # @param command The string you want to send to the serial port
    def isAquery(self,command):    
        if self.amInull():
            return False
        queryOnly=["?","PH","TE","TP","TS","VE"]
        command = command.upper()
        for q in queryOnly:
            if command.find(q) != -1:
                return True
        return False
    

    ## Sends the command you want to the port and, if it's supposed to get an answer it returns the response
    # @params command The string you want to send to the serial port
    def sendString(self,command):
        #self.input_buffer_log.append(self.in_waiting)
        '''input_buffer = self.in_waiting 
        if input_buffer != 0:
            print('Input buffer is nonzero !')
            self.reset_input_buffer()
        '''
        #self.flush()
        response = ''
        command += '\r\n'
        bCommand = command.encode()
        self.write(bCommand)
        sleep(0.05)
        #print('Wrote')
        if self.isAquery(command):
            #print('Trying to read')
            response = self.readline()
            #print(response)
            #print('Read')
        return response
    
    
 