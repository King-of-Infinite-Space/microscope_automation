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
from EOSwindowControl import focusWindow
# from imgUtil import rotateCrop

# CONFIGURATION

# length per step:
# X & Y see below
# Z degree per step = 360 / 2048 = 0.175
today = datetime.datetime.now()
todayStr = today.strftime('%Y_%m_%d')
imgFolderPath = '../Pictures/%s/' % todayStr

# px -> length -> step
# 50x
#  pxPerStep={'X+':6.154, 'X-':6.094, 'Y+':5.844, 'Y-':6.205}  #stage motion
# lenPerPx = 0.085070183

# 20x & 1920
pxPerStep={'X+':0.920, 'X-':0.911, 'Y+':0.873, 'Y-':0.927}
lenPerPx = 0.56926

# for sample stage movement, adjustable
XstridePx = 1000
YstridePx = 1000
Zstride = 30
rotateAngle = 1000  #for rotational stage. roughly 500 steps = 1 deg

jogSpeed = 1700 # 5, 100, 666, 1700
JOGMODE = {'666': 4, '1700': 3, '100': 2, '5':1}

pxSize = 900
#offset = 50 #we'll crop the central square of the image (size: pxSize + offset)

windowName = "Remote Live View window"

comlist = serial.tools.list_ports.comports()
connected = [port.device for port in serial.tools.list_ports.comports()]
print("Connected COM ports: " + str(connected))

stepper = stepperControl.StepperMotor('COM3')
agController = agilisControl.Controller('COM5')

'''
camWindow = EOSwindowControl.WindowMgr()
camWindow.find_window_wildcard("Remote Live View window")
'''

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

def test(ss):
    sampleStageX.resetCounter()
    sampleStageX.timedJog(steps=compensateJog(ss, 'X'))
    print(sampleStageX.queryCounter())
    

def compensateJog(exp, dir):
    # stage movement
    nom = 0
    if dir=='X' and exp > 0:
        nom = 0.9859*exp - 119.27
    if dir=='X' and exp < 0:
        nom = 0.9891*exp + 121.54
    if dir=='Y' and exp > 0:
        nom = 0.986*exp - 119.35
    if dir=='Y' and exp < 0:
        nom = 0.9861*exp + 119.18
    return nom

def initPosition():
    print('Moving to the starting position...')   
    sampleStageX.goMin()
    sampleStageY.goMin()
    while not (sampleStageX.amIstill(200) and sampleStageY.amIstill(200)):
        pass
    sampleStageX.timedJog(speed=1700,steps=compensateJog(5000,'X'))
    sampleStageY.timedJog(speed=1700,steps=compensateJog(5000,'Y'))
    
# time
def moveLens(From, To, mode='jog'):  # move or jog(positive int) 
    dZ = To[2]-From[2]
    stepper.Step(dZ) 
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
    if mode == 'move':
        sampleStageX.move(-1 * dX)
        sampleStageY.move(-1* dY)
    elif mode == 'jog':  #jog mode, # 4 - 666steps/s; 3 - 1700; 2 - 100 steps/s
        # global jogSpeed
        sampleStageX.timedJog(speed=1700,steps=compensateJog(-dX,'X'))
        sampleStageY.timedJog(speed=1700,steps=compensateJog(-dY,'Y'))
    else:
        raise Exception('Moving mode is not defined')
    return -dX,-dY,dZ
        
def joyControl(disabled = None, controller='joystick', moveMode='move'): 
    global jogSpeed
    Xdis, Ydis, Zdis = 0,0,0
    strideMode = '' 
    #moveMode = 4 
    # 4 - 666steps/s; 3 - 1700; 2 - 100 steps/s
    dX, dY, dZ = XstridePx, YstridePx, Zstride

    def inThreshold(value,thres=0.1):
        if value > thres:
            return 1
        if value <= thres and value >= -thres:
            return 0
        if value < -thres:
            return -1

    def tryMoveLens(DX,DY,DZ):
        #might use jog
        nonlocal Xdis, Ydis, Zdis
        before = np.array([sampleStageX.queryCounter(), sampleStageY.queryCounter(),stepper.GetPosition()])
        expected = np.array(moveLens([0,0,0],[DX,DY,DZ], mode='move'))
        rate = 50
        if DZ == 0:
            while not (sampleStageX.amIstill(rate) and sampleStageY.amIstill(rate)):
                pass
        else:
            pass
            #time.sleep(0.1)
        actual = np.array([sampleStageX.queryCounter(), sampleStageY.queryCounter(),stepper.GetPosition()]) - before

        if np.array_equal(expected, actual):
            if sampleStageX.amIatMyLimit() or sampleStageY.amIatMyLimit():
                print("!!-- Stage is at the limit")
            else:    
                Xdis += DX
                Ydis += DY
                Zdis += DZ
                print(actual)
        else:
            raise Exception("Number of steps doesn't match")

    if controller=='joystick':
        pygame.init()
        pygame.joystick.init()   
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        buttons = {}
        buttonList = ['A','B','X','Y','L1', 'R1', 'SELECT','START']
        axes = {}
        axisList = ['LX','LY','LR2','RY','RX']
        prevButtons = {}
        prevAxes = {}
        for b in buttonList:
            prevButtons[b] = 0
        for a in axisList:
            prevAxes[a] = 0
        if moveMode=='move':
            while True:
                for event in pygame.event.get():
                    pass
                for ind, name in enumerate(buttonList):
                    buttons[name] = joystick.get_button(ind)
                axes['LX'], axes['LY'], axes['LR2'], axes['RY'], axes['RX'] = [joystick.get_axis(i) for i in range(5)]
                HATX = joystick.get_hat(0)[0]
                if buttons['START']:
                    pygame.quit()
                    time.sleep(0.2)
                    break
                # changes stride
                if buttons['A']:  
                    if strideMode != 'medium':
                        strideMode = 'medium'
                        dX, dY, dZ = XstridePx, YstridePx, Zstride
                        jogSpeed = 666
                        print('    ' + strideMode +' stride mode ' + str([dX, dY, dZ]))
                if buttons['B']:  
                    if strideMode != 'small':
                        strideMode = 'small'
                        jogSpeed = 100
                        dX, dY, dZ = XstridePx // 5, YstridePx // 5, Zstride // 5
                        print('    '+strideMode +' stride mode ' + str([dX, dY, dZ]))
                if buttons['X']:  
                    if strideMode != 'large':
                        strideMode = 'large'
                        dX, dY, dZ = XstridePx * 5, YstridePx * 5, Zstride * 5
                        jogSpeed = 1700
                        print('    '+strideMode +' stride mode ' + str([dX, dY, dZ]))
                        
                # sample X, Y, rotation
                if disabled != 'X':
                    if inThreshold(axes['RX']) == 1:
                        tryMoveLens(dX,0,0)
                    if inThreshold(axes['RX']) == -1:
                        tryMoveLens(-dX,0,0)
                if disabled != 'Y':
                    if inThreshold(axes['RY']) == -1:
                        tryMoveLens(0,-dY,0)
                    if inThreshold(axes['RY']) == 1:
                        tryMoveLens(0, dY,0)
                if HATX != 0:
                    rotationStage.move(-HATX*rotateAngle)
                # lens z
                if buttons['R1']:  # right knob goes clockwise
                    tryMoveLens(0,0,dZ)
                if axes['LR2'] < -0.99:
                    tryMoveLens(0,0,-dZ)
        '''
        # not working yet
        if moveMode=='jog':
            while True:
                for event in pygame.event.get():
                    pass
                for ind, name in enumerate(buttonList):
                    buttons[name] = joystick.get_button(ind)
                axes['LX'], axes['LY'], axes['LR2'], axes['RY'], axes['RX'] = [joystick.get_axis(i) for i in range(5)]
                HATX = joystick.get_hat(0)[0]
                
                if buttons['START']:
                    pygame.quit()
                    time.sleep(0.2)
                    break
                # changes stride
                if buttons['A']:  
                    if strideMode != 'medium':
                        strideMode = 'medium'
                        dX, dY, dZ = XstridePx, YstridePx, Zstride
                        jogSpeed = 666
                        print('    '+strideMode +' stride mode ' + str([jogSpeed, dZ]))
                if buttons['B']:  
                    if strideMode != 'small':
                        strideMode = 'small'
                        jogSpeed = 100
                        dX, dY, dZ = XstridePx // 5, YstridePx // 5, Zstride // 5
                        print('    '+strideMode +' stride mode ' + str([jogSpeed, dZ]))
                if buttons['X']:  
                    if strideMode != 'large':
                        strideMode = 'large'
                        dX, dY, dZ = XstridePx * 5, YstridePx * 5, Zstride * 5
                        jogSpeed = 1700
                        print('    '+strideMode +' stride mode ' + str([jogSpeed, dZ]))
                        
                # sample X, Y, rotation
                if disabled != 'X':
                    if inThreshold(axes['RX']) == 1 and inThreshold(prevAxes['RX']) ==0: 
                        sampleStageX.jog(-1 * JOGMODE[str(jogSpeed)])
                    if inThreshold(axes['RX']) == 0 and inThreshold(prevAxes['RX']) != 0: 
                        sampleStageX.stop()
                    if inThreshold(axes['RX']) == -1 and inThreshold(prevAxes['RX']) ==0: 
                        sampleStageX.jog(JOGMODE[str(jogSpeed)])

                if disabled != 'Y':
                    if inThreshold(axes['RY']) == -1 and inThreshold(prevAxes['RY']) ==0:
                        sampleStageY.jog(-1 * JOGMODE[str(jogSpeed)])
                    if inThreshold(axes['RY']) == 0 and inThreshold(prevAxes['RY']) != 0: 
                        sampleStageY.stop()
                    if inThreshold(axes['RY']) == 1 and inThreshold(prevAxes['RY']) ==0:
                        sampleStageY.jog(JOGMODE[str(jogSpeed)])
                if HATX != 0:
                    rotationStage.move(-HATX*rotateAngle)
                # lens z
                if buttons['R1']:  # right knob goes clockwise
                    tryMoveLens(0,0,dZ)
                if axes['LR2'] < -0.99:
                    tryMoveLens(0,0,-dZ)
            
                prevButtons= buttons
            '''
            
        '''
            #manipulator
            if buttons['L1']:  #up
                manipulatorZ.move()
            if axes['LR2'] > thres: #down
                manipulatorZ.move()
            if axes['LY'] < -thres:
                manipulatorY.move()
            if axes['LY'] > thres: 
                manipulatorY.move()     
            if axes['LX'] > thres: 
                manipulatorX.move()  
            if axes['LX'] < -thres:                   
                manipulatorX.move() 
            '''
        
    '''
    if controller=='keyboard':
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
        '''
    time.sleep(0.1)
    output = np.array([Xdis, Ydis, Zdis])
    print(output)
    return output

def captureImage(windowName):
    '''
    EOS utility hotkeys
    Shutter release: space bar 
    Change aperture: R open up, J close down. 
    Change focus closer: C gross, T mid, W fine. 
    Change focus to inf: R gross, N mid, V fine.
    '''

    #cam.top_window().SetFocus()    
    #camWindow.set_foreground()
    focusWindow(windowName)
    time.sleep(0.02)
    keyboard.press_and_release('space')
    time.sleep(0.04)
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
    
    totNum = numRows * numCols
  
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
        oldFileList = os.listdir(imgFolderPath)
        captureImage(windowName)
        current = calcLoc(loc)
        info = (loc, current)
        log['trace'].append(info)
        print(('%d / %d '+ str(info)) % (ind+1, totNum))
        try:
            new = calcLoc(scanList[ind+1])
            moveLens(current, new)
            while not (sampleStageX.amIstill(30) and sampleStageY.amIstill(30)):
                pass
            # make sure the photo has been taken
            while len(os.listdir(imgFolderPath))==len(oldFileList):
                time.sleep(0.02)
        except IndexError:
            pass
    return log

def scanArea(size):
    # mm
    if type(size)==int:
        width = size
        height = size
    else:
        width = size[0]
        height = size[1] 
    pxW = round(width*1000 / lenPerPx)
    pxH = round(height*1000 / lenPerPx)
    initPosition()
    print('Please move to the bottom right corner and focus')   
    joyControl()
    print('Moving to the Top Right corner...') 
    toMove = [0,pxH,0]
    moveLens([0,0,0],toMove)
    print('Please adjust position and focus')
    BR2TR = joyControl() + np.array(toMove)

    print('Moving to the Top Left corner...') 
    toMove2 = [-pxW,0,0]
    moveLens([0,0,0],toMove2)
    print('Please adjust position and focus')
    TR2TL = joyControl() + np.array(toMove2)  
    
    BR = -1 * (BR2TR + TR2TL)
    TR = -1 * TR2TL
    
    global oldFileList
    try:
        oldFileList = os.listdir(imgFolderPath)
    except FileNotFoundError:
        os.mkdir(imgFolderPath)
        oldFileList = []
    
    focusWindow(windowName) 
    time.sleep(0.1)
    # Scan from TL to BR
    print('Starting to scan...')
    scan(TR, BR)  
    print('Scan finished')

################################################################
# In[]

# Move the stages near the limit to ensure the scanning range is large enough (now up to ~ 24mm)

initPosition()    

print('Please use the knob move to the bottom right corner and use the joystick to focus')   
joyControl()

print('Please go to the Top Right corner and focus')
BR2TR = joyControl()

print('Please go to the Top Left corner and focus')
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

#camWindow.set_foreground()  
focusWindow(windowName)
time.sleep(0.1)
# Scan from TL to BR
print('Starting to scan...')
scanResult = scan(TR, BR)
 
print('Scan finished')

stepper.CloseSerial()
agController.disconnect()

# In[]
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

# rename (or crop) the files
count = 0
for file in newFileList:
    if file not in oldFileList:
        location = scanResult['trace'][count][0]
        filename = '%s_%dx%d_%d_%d.jpg' % (nowStr, scanResult['size'][0], scanResult['size'][1], location[0], location[1])
        # croppedImg = rotateCrop(imgFolderPath+file, pxSize+offset, output= imgFolderPath+filename)
        os.rename(imgFolderPath+file,imgFolderPath+filename)
        count += 1
        
#print('Image preprocessing finished')
#if input('Do you want to delete the original photos?') == 'y':

print('Done')
