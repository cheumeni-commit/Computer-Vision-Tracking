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


if int(tf.__version__.split('.')[1]) < 4:
    raise ImportError('Please upgrade your tensorflow installation to v1.4.* or later!')
    


def update_parcel_info():
    
    parcelColor  = get_config.color[np.random.randint(0, 3)]
    barcode      = get_config.barcode[np.random.randint(0, 3)]
    destBay      = ""
    postCode     = barcode
    parcelID, timestamp = PIdM.parcelIdGenerator()
    
    for segBay in get_config.confBay['bay']:
        destBay = get_config.confBay['postcode']\
                  [get_config.confBay['bay'].index(segBay)]
       
            
    return {'parcelColor': parcelColor, 
            'barcode':barcode,
            'destBay':destBay, 
            'postCode':postCode, 
            'parcelID':parcelID,
            'timestamp':timestamp}


def newParcel(PIdM):
    
    parcelData = update_parcel_info()
    
    parcel = Parcel(parcelData['parcelID'], parcelData['parcelColor'], 
                    parcelData['timestamp'], [0,0,0,0], [0,0,0,0], 
                    parcelData['barcode'], parcelData['destBay'], 
                    parcelData['postCode'])
    
    parcel.isOutcoming = True
    parcel.isExiting = True
    parcel.lastSeenOnCameraID = 'U000'
    
    return parcel
