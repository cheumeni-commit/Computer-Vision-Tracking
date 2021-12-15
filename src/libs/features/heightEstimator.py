#!/usr/bin/env python3
import numpy as np
from copy import deepcopy

from src.parcels.parcel import Parcel


class HeightEstimator():
    """
    Classe HeightEstimator permet le calcul de la hauteur d'un colis suivi.

    """

    def __init__(self):
        """
        Crée un objet HeightEstimator.
        
        Attributes:
            traceInfo: booléen pour tracer les infos de débuggage.

        Todo:
            Réfléchir aux paramètres possibles et les ajouter au fichier de 
            configuration du ParcelTracker qui crée l'instance de HeightEstimator.
        """
        self.traceInfo = False
        self.timeElapsedForHeightEstimation = 1
        self.xRangeCanEstimate = (0.4, 0.65)
        self.xcenter = 0.33333333
        self.cameraHeight = 2500
        

    def estimateHeight(self, parcels):
        for parcel in parcels:
            xmin = parcel.relativeBox[1]
            if xmin > self.xRangeCanEstimate[0] and xmin < self.xRangeCanEstimate[1]:
                if parcel.heightRef == 0 and parcel.timeHoldingToEstimateHeight == 0:
                    parcel.previousRelativeBox = deepcopy(parcel.relativeBox)
                    parcel.timeHoldingToEstimateHeight += 1
                elif parcel.heightRef == 0:
                    if parcel.timeHoldingToEstimateHeight > self.timeElapsedForHeightEstimation:
                        print(parcel.timeHoldingToEstimateHeight)
                        self._computeHeight(parcel)
                    if parcel.timeHoldingToEstimateHeight > 1 and xmin > self.xRangeCanEstimate[1]:
                        self._computeHeight(parcel)
                    parcel.timeHoldingToEstimateHeight += 1


    def estimateHeightLight(self, parcel):        
        if parcel.relativeBox[1] > 0.05 and parcel.relativeBox[1] < 0.45:
            if parcel.previousRelativeBox[0] == 0:
                parcel.previousRelativeBox = deepcopy(parcel.relativeBox)
            else:
                if parcel.timeHoldingToEstimateHeight > self.timeElapsedForHeightEstimation:
                    self._computeHeight(parcel)
                    parcel.previousRelativeBox = deepcopy(parcel.relativeBox)
                    parcel.timeHoldingToEstimateHeight = 1
                else:
                    parcel.timeHoldingToEstimateHeight += 1
                    

    def _computeHeight(self, parcel):
        xmin1 = parcel.previousRelativeBox[1]
        xmax1 = parcel.previousRelativeBox[3]
        xmin2 = parcel.relativeBox[1]
        xmax2 = parcel.relativeBox[3]
        coef = ((xmax1 - xmin1) - (xmax2 - xmin2)) / ((0.5 - xmin1) - (0.5 - xmin2))
        #print('---H----')
        #print(xmin1,xmax1,xmin2,xmax2,coef)
        parcel.heightRef = coef * self.cameraHeight
        #print(parcel.height, ' vs ', parcel.heightRef)
        #print(parcel.height,xmin1,xmax1)
        
heightEstimator = HeightEstimator()
