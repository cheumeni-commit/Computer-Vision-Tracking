#!/usr/bin/env python3

from multiprocessing import Queue
from threading import Thread
import time

from copy import deepcopy
import cv2
import numpy as np
import os
import tensorflow as tf

from src.config.config import get_config
from src.constants import *
from src.config.directories import directories as dirs
from src.parcelTracker import ParcelTracker
from src.utils.objectDetectionViz import *



if int(tf.__version__.split('.')[1]) < 4:
    raise ImportError('Please upgrade your tensorflow installation to v1.4.* or later!')
    
    
def update_parcel_info():
    
    parcelColor  = get_config.color[np.random.randint(0, 3)]
    barcode      = get_config.barcode[np.random.randint(0, 3)]
    destBay      = ""
    postCode     = barcode
    parcelID, timestamp = PIdM.parcelIdGenerator()
    
    for segBay in get_config.confBay[C_BAY]:
        destBay = get_config.confBay[C_POSTCODE]\
                  [get_config.confBay[C_BAY].index(segBay)]
       
            
    return {C_PARCEL_COLOR: parcelColor, 
            C_BARCODE:barcode,
            C_DESTBAY:destBay, 
            C_POSTCODE:postCode, 
            C_PARCELID:parcelID,
            C_TIMESTAMP:timestamp}


def newParcel(PIdM):
    
    parcelData = update_parcel_info()
    
    parcel = Parcel(parcelData[C_PARCELID], parcelData[C_PARCEL_COLOR], 
                    parcelData[C_TIMESTAMP], [0,0,0,0], [0,0,0,0], 
                    parcelData[C_BARCODE], parcelData[C_DESTBAY], 
                    parcelData[C_POSTCODE])
    
    parcel.isOutcoming = True
    parcel.isExiting = True
    parcel.lastSeenOnCameraID = C_UOOO
    
    return parcel


def loadImageServer(imageQueue, incomingQ): 
    
    root =  dirs
    dirlist = os.listdir(dirs.dir_data)
    PIdM = ParcelIdManager(C_UOOO)
    
    for j in range(0,len(dirlist)-1,2):

        imRoot = root + dirlist[j] +'/'
        imRoot2 = root + dirlist[j+1] + '/'

        images = os.listdir(imRoot)
        images2 = os.listdir(imRoot2)
        #if j > 500:<
        #    break
        #print(imRoot)
        for i in range(min(len(images) - 1, len(images2) - 1)):
            if i > 0 and i+1 < len(images2):
                image = imRoot+ images[i]
                image2 = imRoot2+ images2[i+1]
                if np.random.randint(0,15) == 0:
                    print('New incoming parcel')
                    incomingQ.put(newParcel(PIdM))
                print(images[i])
                if 'jpg' in image and 'jpg' in image2:
                    imageQueue.put([image, image2])
                time.sleep(0.250)
                
                
def draw_bounding_box_on_image(objects):
    
    for i in range(len(objects)):
        ymin, xmin, ymax, xmax = objects[i][2]
        draw_bounding_box_on_image_array(image, ymin, xmin, 
                                         ymax, xmax, 'red',
                                         3, '', True)
        return
    
    
def drawParcel_onImageArray(parcels):
    
    for parcel in parcels:
        drawParcelOnImageArray(parcel, image, 
                               displayString = True)
    return
                
                
def parcelDetection():
    
    # init 
    imageQ = Queue()
    incomingQ = Queue()
    
    liveDetectionProcess = Thread(target=parcelDetectionWorker, args=(imageQ,incomingQ,))
    liveDetectionProcess.start()

    time.sleep(20)
    
    loadImageServer(imageQ, incomingQ)

    return


def parcelDetectionWorker(imageQueue, incomingQ):
    
    configFile =  dirs.dir_config / C_PARCELTRACKER
    parcelTracker = ParcelTracker(configFile, C_TRACKER1)
    parcelTracker2 = ParcelTracker(configFile, C_TRACKER2)

    displayDetection = True
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('F:/CARS_BigOne/Acqui26082020/test.avi', fourcc, 8, (int(1456),544))
    ite = 0
    debugJson = False

    counters = [[],[], [], []]

    while True:
        
        imageStream = imageQueue.get()

        image_cam1 = cv2.imread(imageStream[0])
        image_cam2 = cv2.imread(imageStream[1])
        
        incParcel = None 
        
        while incomingQ.empty() == False:
              incParcel = incomingQ.get()
                
        # tracker 1
        parcels, objects, numObj = parcelTracker.update(image_cam1, [incParcel], 1)

        image_rgb1 = cv2.cvtColor(image_cam1, cv2.COLOR_BGR2RGB)
        
        draw_bounding_box(objects)
            
        drawParcel_onImageArray(parcels)
            
        image_bgr1 = cv2.cvtColor(image_rgb1, cv2.COLOR_RGB2BGR)
        
        # tracker 2
        parcelsCopy = deepcopy(parcels)

        parcels2, objects, numObj = parcelTracker2.update(image_cam2, parcelsCopy, 2)
        
        image_rgb2 = cv2.cvtColor(image_cam2, cv2.COLOR_BGR2RGB)
        
        draw_bounding_box_on_image(objects)
        
        drawParcel_onImageArray(parcels2)
            
        image_bgr2 = cv2.cvtColor(image_rgb2, cv2.COLOR_RGB2BGR) 
        
        # Affichage des images tracker 1&2
        imgout = stackImages(1, [[image, image2]])
        imgout = cv2.resize(imgout, (int(imgout.shape[1]/2),int(imgout.shape[0]/2)))
        out.write(imgout) 
        
        cv2.imshow('Parcel detection', imgout)
        #cv2.waitKey(0)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        ite += 1

        parcelCount(counters, parcels, parcels2)
        print('-------')
        print('Entrant : {} / Sortant cam 1 : {} / Sortant cam 2 :                                                         {}'.format(len(counters[0]),len(counters[3]),len(counters[1])))
    vidcap.release()
    out.release()
    return 


def stackImages(scale, imgArray):
    '''
    '''
    rows = len(imgArray)
    cols = len(imgArray[0])
    rowsAvailable = isinstance(imgArray[0], list)

    width = imgArray[0][0].shape[1]
    heigth =  imgArray[0][0].shape[0]

    if rowsAvailable :
        for row in range(0, rows):
            for col in range(0, cols):
                
                if imgArray[row][col].shape[:2] == imgArray[0][0].shape[:2]:
                    imgArray[row][col] = cv2.resize(imgArray[row][col], (0,0), 
                                                    None, scale, scale)
                    
                else:
                    imgArray[row][col] = cv2.resize(imgArray[row][col], 
                                                    (imgArray[0][0].shape[1], 
                                                     imgArray[0][0].shape[0]),
                                                      None,scale, scale)
                    
                if len(imgArray[row][col].shape) == 2:
                    imgArray[row][col] = cv2.cvtColor(imgArray[row][col],
                                                      cv2.COLOR_GRAY2BGR)
        ## 
        imgBlank = np.zeros((heigth, width, 3), np.uint8)
        hor = [imgBlank]*rows
        hor_con = [imgBlank]*rows
        for row in range(0, rows):
            hor[row] = np.hstack(imgArray[row])
            
        ver = np.vstack(hor)
    else:
        for row in range(0, rows):
            
            if imgArray[row].shape[:2] == imgArray[0].shape[:2]:
                imgArray[row] = cv2.resize(imgArray[row], (0,0), None, scale, scale)
                
            else:
                 imgArray[row] = cv2.resize(imgArray[row], (imgArray[0].shape[1], 
                                                           imgArray[0].shape[0]),
                                                           None, scale, scale)
                    
            if len(imgArray[row].shape) == 2:
                 imgArray[row] = cv2.cvtColor(imgArray[row], cv2.COLOR_GRAY2BGR)
                    
        hor = np.hstack(imgArray)
        ver = hor

    return ver

