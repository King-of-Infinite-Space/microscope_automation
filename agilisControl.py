import sys
sys.path.append('./pyagilis/')
from controller import AGUC8
from channel import Axis

class Controller(AGUC8):
    def __init__(self, portName):
        for i in range(5):
            super().__init__(portName)
            ver = self.port.sendString('VE')
            if not b'AG-UC8' in ver:
                print('Connection failed. Retrying...')
                self.disconnect()
            else:
                print('----Connected to Agilis Controller ' + ver.decode()[:-5])
                break
            if i == 4:
                raise('Connection failed')
        self.devices = []

    def addDevice(self, channel=None, axis=None):
        device = AgilisDevice(channel=channel, axis=axis, controller=self)
        self.devices.append(device)
        return device

class AgilisDevice(Axis):
    def __init__(self, channel=None, axis=None, controller = None, stepAmp = 50):
        super().__init__(name = str(axis), stepAmp = stepAmp, rate = 750,controller = controller)
        if channel not in range(1,5) or axis not in range(1,3):
            raise(ValueError('Please check channel or axis'))
        self.channel=channel
        self.axis=axis
        
    def toMyChannel(self):
        self.controller.chchch(self.channel)
    def move(self, steps):
        if self.controller.currentChannel != self.channel:
            self.toMyChannel()
        super().move(steps)

    