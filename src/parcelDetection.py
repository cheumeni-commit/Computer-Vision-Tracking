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

from config.config import get_config
from constants import (C_PARCELTRACKER,
                       C_TRACKER1,
                       C_TRACKER2,
                       C_BAY,
                       C_POSTCODE,
                       C_PARCEL_COLOR,
                       C_BARCODE,
                       C_DESTBAY,
                       C_PARCELID,
                       C_TIMESTAMP,
                       C_UOOO
                       )
from config.directories import directories as dirs
from parcelTracker import ParcelTracker
from utils.objectDetectionViz import drawParcelOnImageArray
from utils.utils import draw_bounding_box_on_image_array
from parcels.parcel import Parcel
from parcels.parcelIdManager import ParcelIdManager

if int(tf.__version__.split('.')[1]) < 4:
    raise ImportError('Please upgrade your tensorflow installation to v1.4.* or later!')


def update_parcel_info(PIdM):
    parcelColor = get_config('str').color[np.random.randint(0, 3)]
    barcode = get_config('str').barcode[np.random.randint(0, 3)]
    destBay = ""
    postCode = barcode
    parcelID, timestamp = PIdM.parcelIdGenerator()

    for segBay in get_config('str').confBay[C_BAY]:
        destBay = get_config('str').confBay[C_POSTCODE] \
            [get_config('str').confBay[C_BAY].index(segBay)]

    return {C_PARCEL_COLOR: parcelColor,
            C_BARCODE: barcode,
            C_DESTBAY: destBay,
            C_POSTCODE: postCode,
            C_PARCELID: parcelID,
            C_TIMESTAMP: timestamp}


def newParcel(PIdM):
    parcelData = update_parcel_info(PIdM)

    parcel = Parcel(parcelData[C_PARCELID], parcelData[C_PARCEL_COLOR],
                    parcelData[C_TIMESTAMP], [0, 0, 0, 0], [0, 0, 0, 0],
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


def _read_file(kwargs, i, j):
    return dirs.dir_raw / kwargs['image_dir'][i] / kwargs['data_image'][i][j]


def load_image(PIdM, **kwargs):
    nb_min_image = np.min([len(value) for key, value in kwargs['data_image'].items()])

    for i in range(nb_min_image - 1):
        image_raw1 = _read_file(kwargs, 0, i)
        image_raw2 = _read_file(kwargs, 1, i)

        if np.random.randint(0, 15) == 0:
            print('New incoming parcel')
            kwargs['incomingQ'].put(newParcel(PIdM))

        if 'jpg' in kwargs['data_image'][0][i] and 'jpg' in kwargs['data_image'][1][i]:
            kwargs['imageQueue'].put([image_raw1, image_raw2])
        time.sleep(0.250)


def loadImageServer(imageQueue, incomingQ):
    dirlist = os.listdir(dirs.dir_raw)
    PIdM = ParcelIdManager(C_UOOO)

    # load_image(PIdM, **data)
    for j in range(0,len(dirlist)-1,2):

        imRoot = str(dirs.dir_raw) + "/"+ dirlist[j] +'/'
        imRoot2 = str(dirs.dir_raw) +"/"+ dirlist[j+1] + '/'

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

                if 'jpg' in image and 'jpg' in image2:
                    imageQueue.put([image, image2])
                time.sleep(0.250)


def parcelDetection():
    imageQ = Queue()
    incomingQ = Queue()

    liveDetectionProcess = Thread(target=parcelDetectionWorker, args=(imageQ, incomingQ))
    liveDetectionProcess.start()

    time.sleep(20)
    loadImageServer(imageQ, incomingQ)
    print('end of test')

    return None


def parcelDetectionWorker(imageQueue, incomingQ):
    configFile = dirs.dir_config / C_PARCELTRACKER
    parcelTracker1 = ParcelTracker(configFile, C_TRACKER1)
    parcelTracker2 = ParcelTracker(configFile, C_TRACKER2)

    # displayDetection = True
    fps = 8
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    # out = cv2.VideoWriter(dirs.dir_video / 'test.avi', fourcc, fps,(1456,544))
    ite = 0
    # debugJson = False
    # counters = [[] for _ in range(4)]

    while True:
        
        image = imageQueue.get()

        image_cam1 = cv2.imread(str(image[0]))
        image_cam2 = cv2.imread(str(image[1]))

        incParcel = None
        while not incomingQ.empty():
            incParcel = incomingQ.get()
           

        # tracker 1
        parcelS_1 = parcelTracker1.trackerSpace.beltBoundaries
        parcelS_2 = parcelTracker1.trackerSpace.beltBoundaries
        print("beltboundaries", parcelS_1)
        parcels, objects, numObj, inc = parcelTracker1.update(image_cam1, [incParcel], 1)
        # print("object", objects)
        print("Parcels", parcels)
        image = cv2.cvtColor(image_cam1, cv2.COLOR_BGR2RGB)
        if parcelTracker1.zoneAssociation != '':
            # affichage zone de tracking et zone d'association de la detection avec les images envoyées par le systeme (PIC)
            draw_bounding_box_on_image_array(image, parcelTracker1.yMinAss, parcelTracker1.xMinAss, parcelTracker1.yMaxAss,  parcelTracker1.xMaxAss, 'red', 5, '', True)
            draw_bounding_box_on_image_array(image, parcelTracker1.yMinLimit, parcelTracker1.xMinLimit, parcelTracker1.yMaxLimit, parcelTracker1.xMaxLimit, 'green', 5, '', True)
            # affichage limites du convoyeur sous la premiere camera
            draw_bounding_box_on_image_array(image, parcelS_1[0][0], parcelS_1[0][1], parcelS_1[0][2], parcelS_1[0][3], 'blue', 5, '', True)
        

        for i in range(len(objects)):
            ymin, xmin, ymax, xmax = objects[i][2]
            # draw_bounding_box_on_image_array(image, ymin, xmin, ymax, xmax, 'red', 3, '', True)
        # for parcel in parcels:
            # drawParcelOnImageArray(parcel, image, displayString=True)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # tracker 2
        parcelsCopy = deepcopy(parcels)
        parcels2, objects, numObj , inc = parcelTracker2.update(image_cam2, parcelsCopy, 2)
        
        image2 = cv2.cvtColor(image_cam2, cv2.COLOR_BGR2RGB)
        # affichage limites du convoyeur sous la deuxieme camera
        draw_bounding_box_on_image_array(image2, parcelS_2[0][0], parcelS_2[0][1], parcelS_2[0][2], parcelS_2[0][3], 'blue', 5, '', True)
        for i in range(len(objects)):
            ymin, xmin, ymax, xmax = objects[i][2]
            # draw_bounding_box_on_image_array(image2, ymin, xmin, ymax, xmax, 'red', 3, '', True)
        # for parcel in parcels2:
            # drawParcelOnImageArray(parcel, image2, displayString=True)
        image2 = cv2.cvtColor(image2, cv2.COLOR_RGB2BGR)

        imgout = stackImages(1, [[image, image2]])
        imgout = cv2.resize(imgout, (int(imgout.shape[1] / 2), int(imgout.shape[0] / 2)))
        # save frames
        # out.write(imgout)
        # show frames
        cv2.imshow('Parcel detection', imgout)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        ite += 1

    # vidcap.release()
    # out.release()
    return None


def stackImages(scale, imgArray):
    """
    """
    rows = len(imgArray)
    cols = len(imgArray[0])
    rowsAvailable = isinstance(imgArray[0], list)

    width = imgArray[0][0].shape[1]
    heigth = imgArray[0][0].shape[0]

    if rowsAvailable:
        for row in range(0, rows):
            for col in range(0, cols):

                if imgArray[row][col].shape[:2] == imgArray[0][0].shape[:2]:
                    imgArray[row][col] = cv2.resize(imgArray[row][col], (0, 0),
                                                    None, scale, scale)

                else:
                    imgArray[row][col] = cv2.resize(imgArray[row][col],
                                                    (imgArray[0][0].shape[1],
                                                     imgArray[0][0].shape[0]),
                                                    None, scale, scale)

                if len(imgArray[row][col].shape) == 2:
                    imgArray[row][col] = cv2.cvtColor(imgArray[row][col],
                                                      cv2.COLOR_GRAY2BGR)
        ## 
        imgBlank = np.zeros((heigth, width, 3), np.uint8)
        hor = [imgBlank] * rows
        # hor_con = [imgBlank]*rows
        for row in range(0, rows):
            hor[row] = np.hstack(imgArray[row])

        ver = np.vstack(hor)
    else:
        for row in range(0, rows):

            if imgArray[row].shape[:2] == imgArray[0].shape[:2]:
                imgArray[row] = cv2.resize(imgArray[row], (0, 0), None, scale, scale)

            else:
                imgArray[row] = cv2.resize(imgArray[row], (imgArray[0].shape[1],
                                                           imgArray[0].shape[0]),
                                           None, scale, scale)

            if len(imgArray[row].shape) == 2:
                imgArray[row] = cv2.cvtColor(imgArray[row], cv2.COLOR_GRAY2BGR)

        hor = np.hstack(imgArray)
        ver = hor

    return ver
