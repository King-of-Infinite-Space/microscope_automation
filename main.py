# In[]

import numpy as np
import keyboard
import time
import datetime
import os
import pygame
import serial.tools.list_ports

import stepperControl
import agilisControl
import EOSwindowControl
from imgUtil import rotateCrop

# CONFIGURATION

# length per step:
# X & Y see below
# Z degree per step = 360 / 2048 = 0.175
today = datetime.datetime.now()
todayStr = today.strftime('%Y_%m_%d')
imgFolderPath = 'C:\\Users\\fcbar\\Pictures\\%s\\' % todayStr

# px -> length -> step
# 50x
pxPerStep={'X+':6.138, 'X-':5.935, 'Y+':5.974, 'Y-':6.175}  #stage motion
# 20x
#pxPerStep={'X+':2.477, 'X-':2.395, 'Y+':2.411, 'Y-':2.491}

# for sample stage movement, adjustable
XstridePx = 2000
YstridePx = 2000
Zstride = 50
rotateAngle = 1000  #roughly 500 steps = 1 deg

pxSize = 1800 
offset = 100 #we'll crop the central square of the image (size: pxSize + offset)

#stepsPerSide = {key: int(pxSize // value) for key, value in pxPerStep.items()}

comlist = serial.tools.list_ports.comports()
connected = [port.device for port in serial.tools.list_ports.comports()]
print("Connected COM ports: " + str(connected))

stepper = stepperControl.StepperMotor('COM3')
agController = agilisControl.Controller('COM5')
camWindow = EOSwindowControl.WindowMgr()
camWindow.find_window_wildcard("遥控实时显示窗口")

rotationStage = agController.addDevice(channel=3, axis=2)
sampleStageX = agController.addDevice(channel=4, axis=1)
sampleStageY = agController.addDevice(channel=4, axis=2)

manipulatorX = agController.addDevice(channel=1, axis=1)
manipulatorY = agController.addDevice(channel=1, axis=2)
manipulatorZ = agController.addDevice(channel=2, axis=1)


########################################################
# In[]
def calibrateXY():
    stepsPerRange={}
    stepsPerRange['X+'] = sampleStageX.stepsPerRange(1)
    time.sleep(0.1)
    stepsPerRange['X-'] = sampleStageX.stepsPerRange(-1)
    time.sleep(0.1)
    stepsPerRange['Y+'] = sampleStageY.stepsPerRange(1)
    time.sleep(0.1)
    stepsPerRange['Y-'] = sampleStageY.stepsPerRange(-1)
    print(stepsPerRange)
    return stepsPerRange

def test():
    moveLens([0,0,0],[5000,0,0])
    moveLens([5000,0,0],[0,0,0])
    captureImage(camWindow)

def moveLens(From, To):
    # transform px movement to steps
    # lens movement is opposite to stage
    dX = To[0]-From[0]
    if dX > 0:  #lens going right, stage going left
        dX = dX / pxPerStep['X-']
    else:
        dX = dX / pxPerStep['X+']
    dY = To[1]-From[1]
    if dY > 0:
        dY = dY / pxPerStep['Y-']
    else:
        dY = dY / pxPerStep['Y+']        
    dX = round(dX)
    dY = round(dY)
    sampleStageX.move(-1 * dX)
    sampleStageY.move(-1* dY)
    dZ = To[2]-From[2]
    stepper.Step(dZ)
    return -dX,-dY,dZ
        
def joyControl(disabled = None, mode='keyboard'): 
    thres = 0.1
    Xdis, Ydis, Zdis = 0,0,0
    strideMode = 'large'    
    #moveMode = 4 
    # 4 - 666steps/s; 2 - 100 steps/s
    dX, dY, dZ = XstridePx, YstridePx, Zstride
    def tryMoveLens(DX,DY,DZ):
        #might use jog
        nonlocal Xdis, Ydis, Zdis
        before = np.array([sampleStageX.queryCounter(), sampleStageY.queryCounter(),stepper.GetPosition()])
        expected = np.array(moveLens([0,0,0],[DX,DY,DZ]))
        rate = 50
        if DZ == 0:
            while not (sampleStageX.amIstill(rate) and sampleStageY.amIstill(rate)):
                pass
        else:
            pass
            #time.sleep(0.1)
        actual = np.array([sampleStageX.queryCounter(), sampleStageY.queryCounter(),stepper.GetPosition()]) - before
        print(expected)
        print(actual)
        if np.array_equal(expected, actual):
            Xdis += DX
            Ydis += DY
            Zdis += DZ
        else:
            raise Exception("Number of steps doesn't match")

    if mode=='joystick':
        pygame.init()
        pygame.joystick.init()   
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        button = {}
        buttonList = ['A','B','X','Y','L1', 'R1', 'SELECT','START']

        while True:
            for event in pygame.event.get():
                pass
            for ind, name in enumerate(buttonList):
                button[name] = joystick.get_button(ind)
            LX, LY, LR2, RY, RX = [joystick.get_axis(i) for i in range(5)]
            HATX = joystick.get_hat(0)[0]
            
            if button['START']:
                pygame.quit()
                break
            # changes stride
            if button['A']:  
                if strideMode != 'large':
                    strideMode = 'large'
                    dX, dY, dZ = XstridePx, YstridePx, Zstride
                    print('    ' + strideMode +' stride mode ' + str([dX, dY, dZ]))
            if button['B']:  
                if strideMode != 'small':
                    strideMode = 'small'
                    dX, dY, dZ = XstridePx // 10, YstridePx // 10, Zstride //10
                    print('    '+strideMode +' stride mode ' + str([dX, dY, dZ]))
            # sample X, Y, rotation
            if disabled != 'X':
                if RX > thres: 
                    tryMoveLens(dX,0,0)
                if RX < -thres:
                    tryMoveLens(-dX,0,0)
            if disabled != 'Y':
                if RY < -thres:
                    tryMoveLens(0,-dY,0)
                if RY > thres:
                    tryMoveLens(0, dY,0)
            if HATX != 0:
                rotationStage.move(-HATX*rotateAngle)
            # lens z
            if button['R1']:  # right knob goes clockwise
                tryMoveLens(0,0,dZ)
            if LR2 < -0.99:
                tryMoveLens(0,0,-dZ)

            #manipulator
            if button['L1']:  #up
                manipulatorZ.move()
            if LR2 > thres: #down
                manipulatorZ.move()
            if LY < -thres:
                manipulatorY.move()
            if LY > thres: 
                manipulatorY.move()     
            if LX > thres: 
                manipulatorX.move()  
            if LX < -thres:                   
                manipulatorX.move()  
    if mode=='keyboard':
        while True:         
            if keyboard.is_pressed('alt+enter'):
                break
            # changes stride
            if keyboard.is_pressed('alt+a'):  
                if strideMode != 'large':
                    strideMode = 'large'
                    dX, dY, dZ = XstridePx, YstridePx, Zstride
                    print('    ' + strideMode +' stride mode ' + str([dX, dY, dZ]))
                if strideMode != 'small':
                    strideMode = 'small'
                    dX, dY, dZ = XstridePx // 10, YstridePx // 10, Zstride //10
                    print('    '+strideMode +' stride mode ' + str([dX, dY, dZ]))
            # sample X, Y, rotation
            if disabled != 'X':
                if keyboard.is_pressed('alt+l'):  
                    tryMoveLens(dX,0,0)
                if keyboard.is_pressed('alt+j'):    
                    tryMoveLens(-dX,0,0)
            if disabled != 'Y':
                if keyboard.is_pressed('alt+i'):  
                    tryMoveLens(0,-dY,0)
                if keyboard.is_pressed('alt+k'):  
                    tryMoveLens(0, dY,0)
            # lens z
            if keyboard.is_pressed('alt+]'):   # right knob goes clockwise
                tryMoveLens(0,0,dZ)
            if keyboard.is_pressed('alt+['):  
                tryMoveLens(0,0,-dZ)
    time.sleep(0.1)
    output = np.array([Xdis, Ydis, Zdis])
    print(output)
    return output

def calcNumPhotos(mm):
    pxs = 2351*mm/0.2
    num = pxs / 1800
    return num

def captureImage(camWindow):
    '''
    EOS utility hotkeys
    Shutter release: space bar 
    Change aperture: R open up, J close down. 
    Change focus closer: C gross, T mid, W fine. 
    Change focus to inf: R gross, N mid, V fine.
    '''
    oldFileList = os.listdir(imgFolderPath)
    #cam.top_window().SetFocus()    
    camWindow.set_foreground()
    time.sleep(0.1)
    keyboard.press_and_release('space')
    # make sure there is enough time for the photo to be taken
    while len(os.listdir(imgFolderPath))==len(oldFileList):
        time.sleep(0.1)
    #print('Photo taken')
    
# move sample is opposite to move lens
# Scanning path: TL to BR ( right, down, left, down ...)
    
def scan(TR, BR):
    x1, y1, z1 = TR.astype('int64')
    x2, y2, z2 = BR.astype('int64')
    X = max(x1, x2)
    numRows = int(y2 // pxSize) + 2  # num pics along Y   
    numCols = int(X // pxSize) + 2  # num pics along X  # make sure covers entire area
    dzdx = (y2 * z1 - y1 * z2) / (y2 * x1 - y1 * x2)      # Zstep per px along X
    dzdy = (x2 * z1 - x1 * z2) / (x2 * y1 - x1 * y2)    
    
    print("numRows: %d" % numRows)
    print("numCols: %d" % numCols)
  
    log = {'size': (numRows, numCols, pxSize), 'trace':[]}
    
    def calcLoc(ind):  # takes a tuple as input
        X = pxSize * (ind[1] - 1)
        Y = pxSize * (ind[0] - 1)         # Unit: px
        Z = round(dzdx * X + dzdy * Y)  # Unit: step
        new = np.array([X, Y, Z])
        return new
    
    scanList = []
    for j in range(1, numRows+1):
        for i in range(1, numCols+1):
            if (j % 2 == 0): 
                scanList.append((j, numCols - i + 1))
            else:
                scanList.append((j, i))
                          
    for ind, loc in enumerate(scanList):
        captureImage(camWindow)
        current = calcLoc(loc)
        info = (loc, np.copy(current))
        log['trace'].append(info)
        print(info)
        try:
            new = calcLoc(scanList[ind+1])
            moveLens(current, new)
            while not (sampleStageX.amIstill(100) and sampleStageY.amIstill(100)):
                pass
        except IndexError:
            pass

    return log

################################################################
# In[]
    
print('Please move to the bottom right corner and focus')   
joyControl()

print('Please to the Top Right corner and focus')
BR2TR = joyControl()

print('Please to the Top Left corner and focus')
TR2TL = joyControl()

# Convention: right as X+, down as Y+, assuming we are moving the lens' 
# coordinate transform ,now TL as (0,0,0)
BR = -1 * (BR2TR + TR2TL)
TR = -1 * TR2TL

try:
    oldFileList = os.listdir(imgFolderPath)
except FileNotFoundError:
    os.mkdir(imgFolderPath)
    oldFileList = []

camWindow.set_foreground()  
time.sleep(0.2)
# Scan from TL to BR
print('Starting to scan...')
scanResult = scan(TR, BR)
 
print('Scan finished')
print('Starting to process images')
now = datetime.datetime.now()
fmt = '%Y%m%d%H%M'
nowStr = now.strftime(fmt)
# rename the files
# eg. 201808231001_3x4_1_3


numPhotos = scanResult['size'][0] * scanResult['size'][1]
newFileList = os.listdir(imgFolderPath)
for i in range(5):
    if len(newFileList) != len(oldFileList) + numPhotos:
        if i != 4:            
            newFileList = os.listdir(imgFolderPath)    
            time.sleep(1)
        else:
            print('!!  Number of photos doesnt match. Please check.')
    else:
        break
    
count = 0
for file in newFileList:
    if file not in oldFileList:
        location = scanResult['trace'][count][0]
        filename = '%s_%dx%d_%d_%d.jpg' % (nowStr, scanResult['size'][0], scanResult['size'][1], location[0], location[1])
        croppedImg = rotateCrop(imgFolderPath+file, pxSize+offset, output= imgFolderPath+filename)
        count += 1
print('Image preprocessing finished')
#if input('Do you want to delete the original photos?') == 'y':

stepper.CloseSerial()
agController.disconnect()

print('Done')