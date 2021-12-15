#!/usr/bin/env python3

from multiprocessing import Queue
from threading import Thread
from collections import defaultdict
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
from src.parcels.parcel import Parcel
from src.parcels.parcelIdManager import ParcelIdManager



if int(tf.__version__.split('.')[1]) < 4:
    raise ImportError('Please upgrade your tensorflow installation to v1.4.* or later!')
    
    
def update_parcel_info(PIdM):
    
    parcelColor  = get_config('str').color[np.random.randint(0, 3)]
    barcode      = get_config('str').barcode[np.random.randint(0, 3)]
    destBay      = ""
    postCode     = barcode
    parcelID, timestamp = PIdM.parcelIdGenerator()
    
    for segBay in get_config('str').confBay[C_BAY]:
        destBay = get_config('str').confBay[C_POSTCODE]\
                  [get_config('str').confBay[C_BAY].index(segBay)]
       
            
    return {C_PARCEL_COLOR: parcelColor, 
            C_BARCODE:barcode,
            C_DESTBAY:destBay, 
            C_POSTCODE:postCode, 
            C_PARCELID:parcelID,
            C_TIMESTAMP:timestamp}


def newParcel(PIdM):
    
    parcelData = update_parcel_info(PIdM)
    
    parcel = Parcel(parcelData[C_PARCELID], parcelData[C_PARCEL_COLOR], 
                    parcelData[C_TIMESTAMP], [0,0,0,0], [0,0,0,0], 
                    parcelData[C_BARCODE], parcelData[C_DESTBAY], 
                    parcelData[C_POSTCODE])
    
    parcel.isOutcoming = True
    parcel.isExiting = True
    parcel.lastSeenOnCameraID = C_UOOO
    
    return parcel


def image_data(image_dir):
    
    data_image = defaultdict(list)
    for i in np.arange(len(image_dir)):
        data_image[i] = os.listdir(dirs.dir_raw / image_dir[i])
        
    return data_image


def load_image(PIdM, **kwargs):
    
    nb_min_image = np.min([len(value) for key, value in kwargs['data_image'].items()])
    
    for i in range(nb_min_image-1):
        image_raw1 = dirs.dir_raw / kwargs['image_dir'][0] / kwargs['data_image'][0][i]
        image_raw2 = dirs.dir_raw / kwargs['image_dir'][1] / kwargs['data_image'][1][i]
                    
        if np.random.randint(0, 5) == 0:
            print('New incoming parcel')
            kwargs['incomingQ'].put(newParcel(PIdM))
            
        if 'jpg' in kwargs['data_image'][0][i] and 'jpg' in kwargs['data_image'][1][i]:
            kwargs['imageQueue'].put([image_raw1, image_raw2])
        time.sleep(0.250)


def loadImageServer(imageQueue, incomingQ): 
    
    dirlist = os.listdir(dirs.dir_raw)
    PIdM = ParcelIdManager(C_UOOO)
    
    image_dir = sorted([dirlist[i] for i in range(1, len(dirlist))])
    
    data_image = image_data(image_dir)
    
    data = {'imageQueue': imageQueue, 'incomingQ':incomingQ,
           'data_image': data_image, 'image_dir':image_dir}
 
    load_image(PIdM, **data)
                
                
def draw_bounding_box_on_image(objects):
    
    for i in range(len(objects)):
        ymin, xmin, ymax, xmax = objects[i][2]
        draw_bounding_box_on_image_array(image, ymin, xmin, 
                                         ymax, xmax, 'red',
                                         3, '', True)
        return None
    
    
def drawParcel_onImageArray(parcels):
    
    for parcel in parcels:
        drawParcelOnImageArray(parcel, image, 
                               displayString = True)
    return None
                
                
def parcelDetection():
    
    imageQ = Queue()
    incomingQ = Queue()
    
    liveDetectionProcess = Thread(target=parcelDetectionWorker, args=(imageQ,incomingQ,))
    liveDetectionProcess.start()

    time.sleep(20)
    
    loadImageServer(imageQ, incomingQ)

    return None


def imageStream(imageQueue):
    
    imageStream = imageQueue.get()
    
    image_cam1 = cv2.imread(imageStream[0])
    image_cam2 = cv2.imread(imageStream[1])
    
    return {'image_cam1':image_cam1,
            'image_cam2':image_cam2}


def tracker(parcelTracker, dataStream, incParcel, num_cam):
    
    data = parcelTracker.update(dataStream, [incParcel], num_cam)

    image_rgb1 = cv2.cvtColor(dataStream, cv2.COLOR_BGR2RGB)
    
    draw_bounding_box(data['objects'])
    drawParcel_onImageArray(data['parcels'])

    image_bgr1 = cv2.cvtColor(image_rgb1, cv2.COLOR_RGB2BGR)
    
    return {'parcels':parcels, 'objects':objects,
            'numObj':numObj, 'image_bgr1':image_bgr1}
    


def parcelDetectionWorker(imageQueue, incomingQ):
    
    configFile =  dirs.dir_config / C_PARCELTRACKER
    parcelTracker1 = ParcelTracker(configFile, C_TRACKER1)
    parcelTracker2 = ParcelTracker(configFile, C_TRACKER2)

    displayDetection = True
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(dirs.dir_video / 'test.avi',\
                          fourcc, 8,(int(1456),544))
    ite = 0
    debugJson = False

    counters = [[] for _ in range(4)]

    while True:
        
        dataStream = imageStream(imageQueue)
        
        incParcel = None 
        while incomingQ.empty() == False:
              incParcel = incomingQ.get()
                
        #tracker 1
        dataTracker_1 = tracker(parcelTracker1, dataStream['image_cam1'], incParcel, 1)
        
        parcelsCopy = deepcopy(dataTracker_1['parcels'])
        
        # tracker 2
        dataTracker_2 = tracker(parcelTracker2, dataStream['image_cam2'], parcelsCopy, 2)
        
        # Affichage des images tracker 1&2
        imgout = stackImages(1, [[dataStream['image_cam1'], dataStream['image_cam2']]])
        imgout = cv2.resize(imgout, (int(imgout.shape[1]/2),int(imgout.shape[0]/2)))
        # save frames
        out.write(imgout) 
        # show frames
        cv2.imshow('Parcel detection', imgout)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        ite += 1

    vidcap.release()
    out.release()
    return None


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

