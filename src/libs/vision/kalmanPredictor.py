#!/usr/bin/env python3
import numpy as np
import cv2


class KalmanFilterPredictor(object):
    """
    Classe KalmanFilterPredictor permet de prédire la position d'un Parcel.
    Cette classe est essentiellement une surcouche de la classe KalmanFilter
    de OpenCV.
    """

    def __init__(self, fps):
        """
        Construit un objet KalmanFilterPredictor.

        Args:
            fps: la fréquence d'acquisition des images.

        Attributes:
            fps: la fréquence d'acquisition des images.
            kalmanFilter: l'objet KalmanFilter d'open CV.
        """
        self.fps = fps
        
        dt = 1/self.fps #time between 2 acquisitions
        
        self.kalmanFilter = cv2.KalmanFilter(7,4) #7 dynamic parameters (ymin,xmin,ymax,xmax,vy, vxmin, vxmax) and 4 measured parameters (the 4 coordinates)
        self.kalmanFilter.measurementMatrix = np.array([[1,0,0,0,0,0,0], [0,1,0,0,0,0,0],                                                                         [0,0,1,0,0,0,0],\
                                                         [0,0,0,1,0,0,0]], np.float32)
        
        self.kalmanFilter.transitionMatrix = np.array([[1,0,0,0,dt,0,0], [0,1,0,0,0,dt,0],                                                                      [0,0,1,0,dt,0,0],\
                                                       [0,0,0,1,0,0,dt], [0,0,0,0,1,0,0],                                                                       [0,0,0,0,0,1,0],\
                                                       [0,0,0,0,0,0,1]], np.float32)
        
        self.kalmanFilter.measurementNoiseCov = np.array([[0,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,0,0]],\
                                                         np.float32)
    

    def formatMeasurements(self, parcel):
        """
        Formate le tuple de relativeBox d'un Parcel en matrice numpy.

        Args:
            parcel: l'objet parcel.

        Returns:
            La relativeBox d'un Parcel en matrice numpy.
        """
        return np.array(parcel.relativeBox, dtype=np.float32).reshape((4,1))
    

    def setPreviousState(self, parcel):
        """
        Met en place les états précédent d'un Parcel avant la correction et prédiction.
        Cette fonction met la bonne variable statePre ou statePost à jour pour le Parcel.
        
        Args:
            parcel: l'objet parcel à prédire.
        """
        vxmax, vy = parcel.speed
        
        if round(parcel.relativeBox[1], 2) == 0:
            vxmin = 0
        else:
            vxmin = parcel.speed[0]

        if max(parcel.nextRelativeBox) == 0:
            ymin, xmin, ymax, xmax = parcel.relativeBox
            self.kalmanFilter.statePost = np.array([[ymin],[xmin],[ymax],[xmax],[vy],[vxmin],[vxmax]], np.float32)
        else:
            ymin, xmin, ymax, xmax = parcel.nextRelativeBox
            self.kalmanFilter.statePre = np.array([[ymin],[xmin],[ymax],[xmax],[vy],[vxmin],[vxmax]], np.float32)

    def update(self, parcel, measurements):
        """
        Met à jour l'objet Parcel, en réalisant la corrections du filtre de
        Kalman étant donné l'état du Parcel puis en réalisant la prédiction.
        
        Args:
            parcel: l'objet Parcel à prédire.
            measurements: les mesures formatées du parcel pour la correction.
        """
        if max(parcel.nextRelativeBox) != 0:
            self.kalmanFilter.correct(measurements)
            
        predicted = self.kalmanFilter.predict()

        ymin_next = float(predicted[0,0])
        xmin_next = float(predicted[1,0])
        ymax_next = float(predicted[2,0])
        xmax_next = float(predicted[3,0])
        vy_next = float(predicted[4,0])
        #vxmin_next = float(predicted[5,0])
        vxmax_next = float(predicted[6,0])
        
        parcel.nextRelativeBox = (ymin_next, xmin_next, ymax_next, xmax_next) + tuple()
        parcel.speed  = (vxmax_next,vy_next) + tuple() 
        parcel.nextCenter = ((xmin_next + xmax_next) / 2 , (ymin_next + ymax_next) / 2) + tuple()
        
    def updateStates(self, parcels):
        """
        Parcourt la liste des Parcel à prédire et appel les fonctions
        de mises en place et de mise à jour.
        
        Args:
            parcels: liste des Parcel à prédire.
        """
        for parcel in parcels:
            measurements = self.formatMeasurements(parcel)
            self.setPreviousState(parcel)
            self.update(parcel, measurements)
