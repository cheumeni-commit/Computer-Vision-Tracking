#!/usr/bin/env python3
from cars_parcel import Parcel
import numpy as np
from scipy.optimize import linear_sum_assignment
from copy import deepcopy

class ParcelAssociator():
    """
    Classe ParcelAssociator permet l'association d'objets Parcel aux dédections
    réalisés par un ObjectDetector.

    """

    def __init__(self):
        """
        Crée un objet ParcelAssociator.
        
        Attributes:
            traceInfo: booléen pour tracer les infos de débuggage.

        Todo:
            Réfléchir aux paramètres possibles et les ajouter au fichier de 
            configuration du ParcelTracker qui crée l'instance de ParcelAssociator.
        """
        self.traceInfo = False
        self.confidenceThreshold = 0.75


    def associate(self, row_ind, col_ind, parcels, numObj, objects):
        """
        Associe les objets Parcel aux détections par rapport aux résultats
        de l'algorithme d'association utilisé donnant les indices de colonnes
        et de lignes. Cette association consiste à la mise à jour de la 
        relativeBox et du centre par ceux de la détection.

        Args:
            row_ind: liste ordonnée des indices des Parcel à associer aux
            objets détectés d'indice correspondant col_ind.
            col_ind: liste ordonnée des indices des objets détectés à associer 
            aux Parcel d'indice correspondant row_ind.
            parcels: pointeur sur la liste des trackedParcels du ParcelTracker.
            numObj: le nombre d'objets détectés.
            objects: la liste des objets détectés.
        """
        if self.traceInfo:
            print(str(row_ind) + '  ' + str(col_ind))
        ### Association : Mise à des champs du Parcel par les nouvelles données. 
        for i in range(len(row_ind)):
            parcels[row_ind[i]].relativeBox = objects[col_ind[i]][2] + tuple() #python witchcraft : création d'un nouveau tuple pour ne pas pointer sur le tuple d'origine
            parcels[row_ind[i]].center = computeCenterFromRelativeBox(objects[col_ind[i]][2])
            parcels[row_ind[i]].isTracked = True
            parcels[row_ind[i]].isInterpolated = False
            parcels[row_ind[i]].numberOfTimesUndetected = 0
        ### Incrémentation du compteur de chaque Parcel non associé.
        for i in range(len(parcels)):
            if i not in row_ind:
                parcels[i].numberOfTimesUndetected += 1
                parcels[i].isTracked = False
                parcels[i].isInterpolated = True
                parcels[i].relativeBox = deepcopy(parcels[i].nextRelativeBox)
        unassociateDetections = []
        for i in range(numObj):
            if i not in col_ind:
                unassociateDetections.append(i)
        return unassociateDetections

    def computeIOUscoreMatrix(self, parcels, numObj, objects):
        """
        Calcul la matrice des scores basés sur l'IOU. 

        Args:
            parcels: pointeur sur la liste des trackedParcels du ParcelTracker.
            numObj: le nombre d'objets détectés.
            objects: la liste des objets détectés.

        Returns:
            iouMat: la matrice des scores basés sur l'IOU, contenant les scores de
            toutes les paires d'objet/Parcel. La matrice n'est pas forcément carrée.
        """
        iouMat = np.zeros((len(parcels), numObj))
        for i in range(len(parcels)):
            for j in range(numObj):
                ### Calcul du score basé sur l'IOU, score = 1 - IOU
                iouMat[i,j] = computeIOUforRelativeBoxes(parcels[i].nextRelativeBox, objects[j][2])
        return iouMat

    def associateWithIOU(self, parcels, numObj, objects):
        """
        Associe à l'aide d'un algorithme hongrois (linear_sum_assignment)
        les objets aux Parcel avec la matrice des scores basés sur l'IOU. 

        Args:
            parcels: pointeur sur la liste des trackedParcels du ParcelTracker.
            numObj: le nombre d'objets détectés.
            objects: la liste des objets détectés.
        """
        scoreMatrix = self.computeIOUscoreMatrix(parcels, numObj, objects)

        if self.traceInfo:
            print(str(scoreMatrix))
        ### Programmation dynamyque donnant la liste des associations optimales.
        row_ind, col_ind = linear_sum_assignment(scoreMatrix)
        row_ind = row_ind.tolist()
        col_ind = col_ind.tolist()

        ### Blindage suppression des associations pour un score nul
        for i in range(len(row_ind)-1,-1,-1):
            if scoreMatrix[row_ind[i]][col_ind[i]] >= self.confidenceThreshold:
                row_ind.pop(i)
                col_ind.pop(i)
        ### TO DO :
        ### - Vérifier que la matrice de score et le linear_sum est bien fonctionnel.
        ### - Blinder en empêchant une association avec un IOU à 0 (soit un score de 1)
        ### Pour se faire il faut retirer les indices perturbateurs ou reporter le problème
        ### à la fonction associate en transmettant la scoreMatrix aussi (moins bien).
        unassociateDetections = self.associate(row_ind, col_ind, parcels, numObj, objects)
        return unassociateDetections

    def computeCenterEuclidieanDistScoreMatrix(self, parcels, numObj, objects):
        """
        Calcul la matrice des scores basés sur la distance euclidienne des centres. 

        Args:
            parcels: pointeur sur la liste des trackedParcels du ParcelTracker.
            numObj: le nombre d'objets détectés.
            objects: la liste des objets détectés.

        Returns:
            edMat: la matrice des scores basés sur distance euclidienne des centres, 
            contenant les scores de toutes les paires d'objet/Parcel. 
            La matrice n'est pas forcément carrée.
        """
        edMat = np.zeros((len(parcels), numObj))
        for i in range(len(parcels)):
            for j in range(numObj):
                objCenter = computeCenterFromRelativeBox(objects[j][2])
                edMat[i,j] = computeEuclideanDistForCenters(parcels[i].nextCenter, objCenter)
        return edMat
    
    def associateWithEuclidieanDist(self, parcels, numObj, objects):
        """
        Associe à l'aide d'un algorithme hongrois (linear_sum_assignment)
        les objets aux Parcel avec la matrice des scores basés sur la distance euclidienne. 

        Args:
            parcels: pointeur sur la liste des trackedParcels du ParcelTracker.
            numObj: le nombre d'objets détectés.
            objects: la liste des objets détectés.
        """
        scoreMatrix = self.computeCenterEuclidieanDistScoreMatrix(parcels, numObj, objects)
        if self.traceInfo:
            print(str(scoreMatrix))
        row_ind, col_ind = linear_sum_assignment(scoreMatrix)
        self.associate(row_ind, col_ind, parcels, numObj, objects)

    def associateWithIOUandEuclidieanDist(self, parcels, numObj, objects):
        """
        Associe à l'aide d'un algorithme hongrois (linear_sum_assignment)
        les objets aux Parcel avec la matrice produit de la matrice des scores 
        basés sur l'IOU et celle des scores basés sur la distance euclidienne. 

        Args:
            parcels: pointeur sur la liste des trackedParcels du ParcelTracker.
            numObj: le nombre d'objets détectés.
            objects: la liste des objets détectés.
        """
        scoreMatrixIOU = self.computeIOUscoreMatrix(parcels, numObj, objects)
        scoreMatrixED = self.computeCenterEuclidieanDistScoreMatrix(parcels, numObj, objects)
        scoreMatrix = scoreMatrixIOU * scoreMatrixED
        if self.traceInfo:
            print(str(scoreMatrix))
        row_ind, col_ind = linear_sum_assignment(scoreMatrix)
        self.associate(row_ind, col_ind, parcels, numObj, objects)
        

def computeCenterFromRelativeBox(rBox):
    """
    Calcul le centre d'une realtiveBox (d'un rectangle).

    Args:
        rBox: la relative box contenant les coordonnées (ymin,xmin,ymax,xmax).

    Returns:
        Le centre de la relativeBox (x,y).
    """
    return ((rBox[3] + rBox[1]) / 2 , (rBox[2] + rBox[0]) / 2)

def computeEuclideanDistForCenters(center, objCenter):
    """
    Calcul la distance euclidienne entre deux centres.

    Args:
        center: le centre du Parcel.
        objCenter: le centre de l'objet détecté.

    Returns:
        La distance euclidienne entre les centres.
    """
    return np.linalg.norm([center[0]-objCenter[0], center[1]-objCenter[1]])


def computeIOUforRelativeBoxes(relativeBox, objRelativeBox):
    """
    Calcul le score IOU entre deux relativeBox. Le score est égal à 1 - IOU.

    Args:
        relativeBox: la nextRelativeBox d'un Parcel.
        objRelativeBox: la relativeBox d'un objet détecté.

    Returns:
        Le score égal à 1 - IOU.
    """
    yg_min, xg_min, yg_max, xg_max = relativeBox
    yp_min, xp_min, yp_max, xp_max = objRelativeBox
    
    #calculate the coordiantes of the intersection rectangle
    x1 = max(xg_min, xp_min)
    y1 = max(yg_min, yp_min)
    x2 = min(xg_max, xp_max)
    y2 = min(yg_max, yp_max)
    if x1 > x2:
        inter = 0
    else:
        if y1 < y2:
            inter = (x2 - x1) * (y2 - y1)
        else:
            inter = 0   
    
    #calculate the union 
    groundtruth_area = (xg_max - xg_min) * (yg_max - yg_min)
    predicted_area = (xp_max - xp_min) * (yp_max - yp_min)
    union = (groundtruth_area + predicted_area) - inter
    
    #calculate_iou
    iou = inter / union
    return 1 - iou
