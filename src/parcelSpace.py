#!/usr/bin/env python3
from src.parcels.parcel import Parcel
import configparser as cfg
import os
import traceback

import cv2
import numpy as np

#from object_detector.ObjectDetector import ObjectDetector
from src.utils.utils import draw_bounding_box_on_image_array


class TrackerSpace():
    """
    Classe TrackerSpace définit l'espace de tracking du tracker.
    Il définit tout ce qui se trouve dans le champ caméra du tracker avec les positions réelles.
    """

    def __init__(self, configFile, trackerName = 'DEFAULT'):
        
        self.beltBoundaries = []
        self.primeAssociationAreas = dict()
        self.zoneUnit0 = ''
        
        self._loadConfig(configFile, trackerName)
        
        self.cameraMatrix = self.cameraCalibration['cameraMatrix']
        self.distortionCoeff = self.cameraCalibration['distortionCoeff']
        self.undistortionMapx = self.cameraCalibration['mapx']
        self.undistortionMapy = self.cameraCalibration['mapy']
        ## info pour dessiner zone tracking sur le convoyeur sur l'image
        self.xMin, self.yMin = self.beltBoundaries[0][1], self.beltBoundaries[0][0]   
        self.xMax, self.yMax = self.beltBoundaries[0][3], self.beltBoundaries[0][2] 
        ## info limite suivant l'axe sur le convoyeur
        self.xMinLimit, self.xMaxLimit = self.getBeltRealPointCoordinatesForScene((self.beltBoundaries[0][1], self.beltBoundaries[0][3]))
        ## zone association
        if self.zoneUnit0 != '':
            self.xMinAss, self.yMinAss = self.primeAssociationAreas[self.zoneUnit0][1], self.primeAssociationAreas[self.zoneUnit0][0]   
            self.xMaxAss, self.yMaxAss = self.primeAssociationAreas[self.zoneUnit0][3], self.primeAssociationAreas[self.zoneUnit0][2]


    def _loadConfig(self, configFile, trackerName):
        """

        """
        config = cfg.ConfigParser()
        config.read(configFile)
        try :
            beltBoundariesStr = config.get(trackerName, 'beltBoundaries')
            primeAssociationAreasStr = config.get(trackerName, 'primeAssociationZones')
            realPositionOfCenterStr = config.get(trackerName, 'realPositionOfCenter')
            quadraticResolutionCoefficientStr = config.get(trackerName, 'quadraticResolutionCoefficientStr')
            cameraCalibrationStr = config.get(trackerName, 'cameraCalibration')
            imageCenterStr = config.get(trackerName, 'imageCenter')
            imageSizeStr = config.get(trackerName, 'imageSize')
            self.cameraHeight = config.getint(trackerName, 'cameraHeight')
            self.deltaImageBoundary = config.getfloat(trackerName, 'deltaImageBoundary')
            self.yGapWithPreviousCam = config.getfloat(trackerName, 'yGapWithPreviousCam')
            self.doUndistortion = config.getboolean(trackerName, 'doUndistortion')
            
            for boundary in beltBoundariesStr.split(';'):
                bs = [float(x) for x in boundary.split(',')]
                self.beltBoundaries.append((bs[0], bs[1], bs[2], bs[3]))
            self.realPositionOfCenter = (float(realPositionOfCenterStr.split(',')[0]),
                                        float(realPositionOfCenterStr.split(',')[1]))
            self.imageCenter = (float(imageCenterStr.split(',')[0]), float(imageCenterStr.split(',')[1]))
            self.imageSize = (float(imageSizeStr.split(',')[0]), float(imageSizeStr.split(',')[1]))
            self.quadraticResolutionCoefficient = (float(quadraticResolutionCoefficientStr.split(',')[0]),
                                               float(quadraticResolutionCoefficientStr.split(',')[1]),
                                               float(quadraticResolutionCoefficientStr.split(',')[2]))
            self.cameraCalibration = np.load(cameraCalibrationStr)
            
            if primeAssociationAreasStr != '':
                for zone in primeAssociationAreasStr.split(';'):
                    self.zoneUnit0 = zone.split(',')[0]
                    zs = [float(x) for x in zone.split(',')[1:]]
                    self.primeAssociationAreas[self.zoneUnit0] = (zs[0], zs[1], zs[2], zs[3])

        except Exception as e:
            if not os.path.isfile(configFile): 
                print('No such config file : ' + configFile)     
                print(str(e))
                print(traceback.format_exc())          
                raise SystemExit('No such config file : ' + configFile)
            else :
                print('Problem loading configuration file : ' + configFile)
                print(str(e))
                print(traceback.format_exc())
                raise SystemExit('Problem loading configuration file : ' + configFile)
            
    def isInBeltBoundaries(self, bbox):
        for boundary in self.beltBoundaries:
            if isInDelimitedArea(bbox, boundary):
                return True
        return False

    def isInPrimeAssociationArea(self, bbox):
        for area in self.primeAssociationAreas:
            if isInDelimitedArea(bbox, self.primeAssociationAreas[area]):
                return True, area
        return False, None

    def getBeltRealPointCoordinatesForScene(self, point):

        resolution = self.quadraticResolutionCoefficient[-1]
        ximg, yimg = point
        xsc        = self.realPositionOfCenter[0] - int(((ximg - self.imageCenter[0]) * self.imageSize[0]))/ resolution 
        ysc        = self.realPositionOfCenter[1] + int(((yimg - self.imageCenter[1]) * self.imageSize[1]))/ resolution 

        return xsc, ysc
    
    def getBeltCoordinates(self, parcel):
        ymin, xmin, ymax, xmax = parcel.relativeBox
        resolution = self.__getResolution(parcel.height)
        resolutionHeight0 = self.quadraticResolutionCoefficient[-1]

        if xmin <= self.imageCenter[0] and xmax >= self.imageCenter[0]:
            xminbelt = self.realPositionOfCenter[0] + (xmin - self.imageCenter[0]) * self.imageSize[0] / resolution
            xmaxbelt = self.realPositionOfCenter[0] + (xmax - self.imageCenter[0]) * self.imageSize[0] / resolution
        elif xmin > self.imageCenter[0]:
            xminbelt = self.realPositionOfCenter[0] + (xmin - self.imageCenter[0]) * self.imageSize[0] / resolutionHeight0
            xmaxbelt_1 = (xmax - self.imageCenter[0]) * self.imageSize[0] / resolutionHeight0
            if xmax > 1 - self.deltaImageBoundary and parcel.widthRef[0] == 0:
                xmaxbelt = self.realPositionOfCenter[0] + xmaxbelt_1
            elif xmax > 1 - self.deltaImageBoundary and parcel.widthRef[0] > 0:
                xmaxbelt = xminbelt + parcel.widthRef[0]
            else:
                xmaxbelt = self.realPositionOfCenter[0] + xmaxbelt_1 * (1 - parcel.height / self.cameraHeight)
        elif xmax < self.imageCenter[0]:
            xmaxbelt = self.realPositionOfCenter[0] + (xmax - self.imageCenter[0]) * self.imageSize[0] / resolutionHeight0
            xminbelt_1 = abs(xmin - self.imageCenter[0]) * self.imageSize[0] / resolutionHeight0
            if xmin < 0 + self.deltaImageBoundary and parcel.widthRef[0] == 0:
                xminbelt = self.realPositionOfCenter[0] - xminbelt_1
            elif xmin < 0 + self.deltaImageBoundary and parcel.widthRef[0] > 0:
                xminbelt = xmaxbelt - parcel.widthRef[0]
            else:
                xminbelt = self.realPositionOfCenter[0] - xminbelt_1 * (1 - parcel.height / self.cameraHeight)

        if ymin <= self.imageCenter[1] and ymax >= self.imageCenter[1]:
            yminbelt = self.realPositionOfCenter[1] + (ymin - self.imageCenter[1]) * self.imageSize[1] / resolution
            ymaxbelt = self.realPositionOfCenter[1] + (ymax - self.imageCenter[1]) * self.imageSize[1] / resolution
        elif ymin > self.imageCenter[1]:
            yminbelt = self.realPositionOfCenter[1] + (ymin - self.imageCenter[1]) * self.imageSize[1] / resolutionHeight0
            ymaxbelt_1 = (ymax - self.imageCenter[1]) * self.imageSize[1] / resolutionHeight0
            if ymax > 1 - self.deltaImageBoundary and parcel.widthRef[1] == 0:
                ymaxbelt = self.realPositionOfCenter[1] + ymaxbelt_1
            elif ymax > 1 - self.deltaImageBoundary and parcel.widthRef[1] > 0:
                ymaxbelt = yminbelt + parcel.widthRef[1]
            else:
                ymaxbelt = self.realPositionOfCenter[1] + ymaxbelt_1 * (1 - parcel.height / self.cameraHeight)                
        elif ymax < self.imageCenter[1]:
            ymaxbelt = self.realPositionOfCenter[1] + (ymax - self.imageCenter[1]) * self.imageSize[1] / resolutionHeight0
            yminbelt_1 = abs(ymin - self.imageCenter[1]) * self.imageSize[1] / resolutionHeight0
            yminbelt = self.realPositionOfCenter[1] - yminbelt_1 * (1 - parcel.height / self.cameraHeight)
            if ymin < 0 + self.deltaImageBoundary and parcel.widthRef[1] == 0:
                yminbelt = self.realPositionOfCenter[1] - yminbelt_1
            elif ymin < 0 + self.deltaImageBoundary and parcel.widthRef[1] > 0:
                yminbelt = ymaxbelt - parcel.widthRef[1]
            else:
                yminbelt = self.realPositionOfCenter[1] - yminbelt_1 * (1 - parcel.height / self.cameraHeight)

        return yminbelt, xminbelt, ymaxbelt, xmaxbelt

    def getRealPointCoordinatesForImage(self, x, y, height):
        resolution = self.__getResolution(height)
        ximg       = ((x - self.realPositionOfCenter[0]) / self.imageSize[0] * resolution + self.imageCenter[0]) * self.imageSize[0]
        yimg       = ((y - self.realPositionOfCenter[1]) / self.imageSize[1] * resolution + self.imageCenter[1]) * self.imageSize[1]
        ### ne gere pas les depassements
        return int(yimg), int(ximg)

    def getBeltCoordinatesForImage(self, beltCoordinates):        
        y1 = ((beltCoordinates[0] - self.realPositionOfCenter[1]) * self.quadraticResolutionCoefficient[-1] / self.imageSize[1] + self.imageCenter[1]) #* self.imageSize[1]
        x1 = ((beltCoordinates[1] - self.realPositionOfCenter[0]) * self.quadraticResolutionCoefficient[-1] / self.imageSize[0] + self.imageCenter[0]) #* self.imageSize[0]
        y2 = ((beltCoordinates[2] - self.realPositionOfCenter[1]) * self.quadraticResolutionCoefficient[-1] / self.imageSize[1] + self.imageCenter[1]) #* self.imageSize[1]
        x2 = ((beltCoordinates[3] - self.realPositionOfCenter[0]) * self.quadraticResolutionCoefficient[-1] / self.imageSize[0] + self.imageCenter[0]) #* self.imageSize[0]
        
        ### Gère les objets très longs:
        y1 = max(0, y1) 
        x1 = max(0, x1)
        y2 = min(self.imageSize[1], y2)
        x2 = min(self.imageSize[0], x2)
        return (y1, x1, y2, x2)

    def getImageCoordinates(self, parcel):
        xmin, xmax = parcel.xPosition
        ymin, ymax = parcel.yPosition
        resolutionHeight0 = self.quadraticResolutionCoefficient[-1]
        resolution = self.__getResolution(parcel.height)
        
        if xmin <= self.realPositionOfCenter[0] and xmax >= self.realPositionOfCenter[0]:
            xminimg = (xmin - self.realPositionOfCenter[0]) / self.imageSize[0] * resolution + self.imageCenter[0]
            xmaximg = (xmax - self.realPositionOfCenter[0]) / self.imageSize[0] * resolution + self.imageCenter[0]
        elif xmin > self.realPositionOfCenter[0]:
            xminimg = (xmin - self.realPositionOfCenter[0]) / self.imageSize[0] * resolutionHeight0 + self.imageCenter[0]
            xmaximg_1 = (xmax - self.realPositionOfCenter[0]) / self.imageSize[0] * resolutionHeight0
            xmaximg = (-1 * xmaximg_1 * self.cameraHeight) / (parcel.height - self.cameraHeight) + self.imageCenter[0]
        elif xmax < self.realPositionOfCenter[0]:
            xmaximg = (xmax - self.realPositionOfCenter[0]) / self.imageSize[0] * resolutionHeight0 + self.imageCenter[0]
            xminimg_1 = (xmin - self.realPositionOfCenter[0]) / self.imageSize[0] * resolutionHeight0
            xminimg = (-1 * xminimg_1 * self.cameraHeight) / (parcel.height - self.cameraHeight) + self.imageCenter[0]

        if ymin <= self.realPositionOfCenter[1] and ymax >= self.realPositionOfCenter[1]:
            yminimg = (ymin - self.realPositionOfCenter[1]) / self.imageSize[1] * resolution + self.imageCenter[1]
            ymaximg = (ymax - self.realPositionOfCenter[1]) / self.imageSize[1] * resolution + self.imageCenter[1]
        elif ymin > self.realPositionOfCenter[1]:
            yminimg = (ymin - self.realPositionOfCenter[1]) / self.imageSize[1] * resolutionHeight0 + self.imageCenter[1]
            ymaximg_1 = (ymax - self.realPositionOfCenter[1]) / self.imageSize[1] * resolutionHeight0
            ymaximg = (-1 * ymaximg_1 * self.cameraHeight) / (parcel.height - self.cameraHeight) + self.imageCenter[1]
        elif ymax < self.realPositionOfCenter[1]:
            ymaximg = (ymax - self.realPositionOfCenter[1]) / self.imageSize[1] * resolutionHeight0 + self.imageCenter[1]
            yminimg_1 = (ymin - self.realPositionOfCenter[1]) / self.imageSize[1] * resolutionHeight0
            yminimg = (-1 * yminimg_1 * self.cameraHeight) / (parcel.height - self.cameraHeight) + self.imageCenter[1]
        
        xminimg = max(xminimg, 0)
        yminimg = max(yminimg, 0)
        return yminimg, xminimg, ymaximg, xmaximg


    
    def __getResolution(self, height):        
        x = float(height)
        a, b, c = self.quadraticResolutionCoefficient
        return a * x * x + b * x + c


    def undistortImage(self, image):
        undistortedImage = cv2.remap(image, self.undistortionMapx, self.undistortionMapy, cv2.INTER_LINEAR)

        return undistortedImage
    
    def __undistortImageWithParamsRecompute(self, image):
        ### Cher en temps et bon on veut pas recalculer
        h,  w = image.shape[:2]         

        # recalculer la camera matrix ne marche pas bien et casse la résolution constante en x et y
        #newCameraMatrix, roi = cv2.getOptimalNewCameraMatrix(self.cameraMatrix, self.distortionCoeff, (w,h), 1, (w,h))
        mapx, mapy = cv2.initUndistortRectifyMap(self.cameraMatrix, self.distortionCoeff, None, self.cameraMatrix, (w,h), 5)
        undistortImage = cv2.remap(image, mapx, mapy, cv2.INTER_LINEAR)

        x, y, w, h = roi
        return undistortImage[y:y+h, x:x+w]

def isInDelimitedArea(bbox, area):

    yminArea, xminArea, ymaxArea, xmaxArea = area
    ymin, xmin, ymax, xmax = bbox
    ymoymin = ymin + (ymax - ymin) / 2
    if ymoymin > yminArea and ymoymin < ymaxArea and xmax > xminArea and xmin < xmaxArea:

        return True
    return False


