#!/usr/bin/env python3
import logging
import configparser as cfg
import datetime
import traceback
import time

import os

from src.config.directories import directories as dirs
from src.libs.features.featuresExtractor import setParcelsWidthRef
from src.libs.features.heightEstimator import HeightEstimator
from src.libs.features.detection import detectAndFilterParcels
from src.libs.fasterObjectDetection.detector import ObjectDetector
from src.libs.vision.parcelAssociator import ParcelAssociator
from src.libs.vision.detectionTracker import DetectionTracker
from src.libs.motion.peer2peerTracker import Peer2peerTracker
from src.parcelSpace import TrackerSpace
from src.parcels.parcelIdManager import ParcelIdManager



COLORS = ['Blue', 'Cyan', 'Orange', 'DeepPink',
          'LawnGreen', 'Lime', 'Purple', 'Green',
          'Turquoise', 'Violet', 'Yellow','Magenta']

logger = logging.getLogger(__name__)

      
class ParcelTracker():
    """
    Classe ParcelTracker permettant le suivi de colis.

    Todo:
        Ajouter une liste de FantomParcels. Les Parcels fantôme répondent au besoin
        de créer des objets hors ud début de champ de vision et permettrait de recréer un
        objet réinsérer au milieu du convoyeur. Il permettrai également de gérer les fausses détections.
    """

    def __init__(self, configFile, trackerType = 'DEFAULT', logger = None):
        """
        Crée un objet ParcelTracker.

        Args:
            configFile: fichier de configuration a charger.
            trackerType: section du fichier de configuration a charger.

        Attributes:        
            trackedParcels: la liste des Parcel trackés.
            incomingParcels: la liste des Parcel à venir.

            Attributs récupérés dans le fichier de config.
            unitName: Nom unique de l'unité tracker.
            traceInfo: booléen pour le traçage d'infos de debug.
            fps: vitesse d'acquisition du banc.
            numberOfTimeUndedectedThreshold: seuil à partir duquel on arrête la prédiction
                d'un objet non détecté et son suivi, le considérant comme retiré. (il peut
                être perdu)
        """
        
        self.logger = logger
        self._loadConfig(configFile, trackerType)
        
        self.parcelDetector = ObjectDetector(dirs.dir_model / self.PATH_TO_CKPT, 
                                             dirs.dir_labels / self.PATH_TO_LABELS,
                                             self.detectionThreshold, self.gpuNum,
                                             self.gpuMemoryFraction)

        self.PIdM = ParcelIdManager(self.unitName)
        self.colors = COLORS
        self.trackedParcels = []
        self.incomingParcels = []
        self.fakeParcels = dict()
        self.parcelInfo = self.newParcel()
        
        self.PA = ParcelAssociator()
        self.HE = HeightEstimator()
        self.detectionTracker = DetectionTracker(self.fps)
        self.trackerSpace = TrackerSpace(self.trackerSpaceConfig, self.unitName)
        
        ## info pour dessiner zone tracking sur le convoyeur sur l'image
        self.xMinLimit, self.yMinLimit = self.trackerSpace.xMin, self.trackerSpace.yMin
        self.xMaxLimit, self.yMaxLimit = self.trackerSpace.xMax, self.trackerSpace.yMax
        ## ## zone association
        self.zoneAssociation = self.trackerSpace.zoneUnit0
        if self.zoneAssociation != '':
            self.xMinAss, self.yMinAss =  self.trackerSpace.xMinAss, self.trackerSpace.yMinAss
            self.xMaxAss, self.yMaxAss =  self.trackerSpace.xMaxAss, self.trackerSpace.yMaxAss

        self.p2pTracker = Peer2peerTracker()

  

    def _loadConfig(self, configFile, trackerType):
        """
        Charge le fichier de configuration du ParcelTracker.

        Args:
            configFile: fichier de configuration a charger.
            trackerType: section du fichier de configuration a charger.

        Raises:
            SystemExit: quitte le programme en cas d'echec du chargement.
        """
        config = cfg.ConfigParser()
        config.read(configFile)
        
        try :
            self.traceInfo = config.getboolean(trackerType, 'traceInfo')
            self.fps = config.getfloat(trackerType, 'fps')
            self.unitName = config.get(trackerType, 'unitName')
            self.numberOfTimeUndedectedThreshold = config.getint(trackerType,
                                                   'numberOfTimeUndedectedThreshold')
            self.numberOfTimeUndedectedThresholdPicked = config.getint(trackerType,
                                                    'numberOfTimeUndedectedThresholdPicked')
            
            self.PATH_TO_CKPT =  config.get(trackerType, 'PATH_TO_CKPT')
            self.PATH_TO_LABELS =  config.get(trackerType, 'PATH_TO_LABELS')
            self.gpuNum =  config.get(trackerType, 'gpuNum')
            self.gpuMemoryFraction =  config.getfloat(trackerType, 'gpuMemoryFraction')
            self.detectionThreshold =  config.getfloat(trackerType, 'detectionThreshold')
            self.trackerSpaceConfig = config.get(trackerType, 'trackerSpaceConfig')
            self.areaConfidenceThreshold =  config.getfloat(trackerType, 'areaConfidenceThreshold')
            self.xLimitParcel =  config.getint(trackerType, 'xLimitParcel')
            self.defaultHeight =  config.getint(trackerType, 'defaultHeight')
            self.secondsToIgnore =  config.getint(trackerType, 'secondsToIgnore')
            
        except Exception as e:
            if not os.path.isfile(configFile): 
                self.logger.info('No such config file : ' + configFile)     
                self.logger.info(str(e))
                self.logger.info(traceback.format_exc())          
                raise SystemExit('No such config file : ' + configFile)
            else :
                self.logger.info('Problem loading configuration file : ' + configFile)
                self.logger.info(str(e))
                self.logger.info(traceback.format_exc())
                raise SystemExit('Problem loading configuration file : ' + configFile)
    

    def __getIncomingParcelByID(self, parcelID):
        for parcel in self.incomingParcels:
            if parcel.parcelID == parcelID:
                return parcel
            
            
    def __updateRelativeBox(self, filteredIncomingParcels):
        
        for incomingParcel in filteredIncomingParcels:
            parcelsID = [parcel.parcelID for parcel in self.incomingParcels] + [parcel.parcelID for parcel in self.trackedParcels]
            
            if 'U0' not in incomingParcel.lastSeenOnCameraID:
                
                ymin, xmin, ymax, xmax = self.trackerSpace.getImageCoordinates(incomingParcel)
                incomingParcel.relativeBox = (ymin, xmin, ymax, xmax)
                incomingParcel.nextRelativeBox = (ymin, xmin, ymax, xmax)
                
                if incomingParcel.parcelID in [parcel.parcelID for parcel in self.incomingParcels]:
                    
                    parcel = self.__getIncomingParcelByID(incomingParcel.parcelID)
                    parcel.relativeBox = incomingParcel.relativeBox + tuple()
                    parcel.nextRelativeBox = incomingParcel.nextRelativeBox + tuple()
                    
            if incomingParcel.parcelID not in parcelsID:
                self.incomingParcels.append(incomingParcel)
                self.incomingParcels[-1].isExiting = False
                self.incomingParcels[-1].isTracked = False
                self.incomingParcels[-1].isInterpolated = True
    

    def _filterIncomingParcels(self, incomingParcels):
        """
        Filtre les paquets provenant de l'unité précédente en ne gardant que 
        les paquets à venir (isOutcoming==True).

        Args:
            incomingParcels: Parcels venant de l'unité précédente.

        """
        if incomingParcels != [None]:
            filteredIncomingParcels = [parcel for parcel in incomingParcels if (parcel.isOutcoming and parcel.isExiting) and parcel.xPosition[1] > self.trackerSpace.xMinLimit]
            
            self.__updateRelativeBox(filteredIncomingParcels)
            
    
    def __fakeParcel(self, numObj, objects):
        
        self.parcelInfo = self.newParcel()
        
        for i, _ in enumerate(numObj):
            self.fakeParcels["parcelID"] = self.PIdM.parcelIdGenerator()[0]
            self.fakeParcels["NR"] = str(objects[i][1])
            self.fakeParcels["bbox"] = objects[i][2]
            self.parcelInfo["fakeParcel"].append(self.fakeParcels)
            
            
    def _manageIncomingAndNewParcels(self, numObj, objects, unassociateDetections):
        """
        Gère les paquets entrants nouveaux ou provenant de l'unité précédente.
        Ajoute d'abord aux Parcels suivi le ou les Parcels à venir s'il y en a,
        sinon cree un nouveau Parcel.

        Args:
            numObj: le nombre d'objets detectes.
            objects: la liste des objets detectes.

        Todo:
            -Gérer les incomingParcel en leur modifiant leur valeur de xmin, xmax,
            dans le nouveau repère caméra, cela permettra une association avec deux
            colis de front arrivant en même temps grâce à leur position y à la caméra 
            précédente.
            -Lorsque le seuil de création interdit la création d'un objet créer un objet fantôme.
        """

        self.__fakeParcel(numObj, objects)
        
        if len(self.incomingParcels) != 0:
            unassociatedObjects = [objects[i] for i in range(numObj)
                                   if i in unassociateDetections]
                    
            unassociateDetections2 = self.PA.associateWithIOU(self.incomingParcels,
                                                              len(unassociatedObjects), 
                                                               unassociatedObjects)

            for i in range(len(self.incomingParcels) - 1, -1, -1):
                if 'U0' not in self.incomingParcels[i].lastSeenOnCameraID:
                    if self.incomingParcels[i].isTracked:
                        self.trackedParcels.append(self.incomingParcels.pop(i))
                        self.trackedParcels[-1].isOutcoming = False
                        self.trackedParcels[-1].lastSeenOnCameraID = self.unitName
                        
                    elif (self.incomingParcels[i].numberOfTimesUndetected >                                                             self.numberOfTimeUndedectedThreshold) or (
                        self.incomingParcels[i].xPosition[0] > self.trackerSpace.xMinLimit):
                        self.trackedParcels.append(self.incomingParcels.pop(i))
                        self.trackedParcels[-1].isOutcoming = False
                        
            # gestion parcel cam1        
            for j in range(len(self.incomingParcels)-1, -1, -1):
                if 'U0' in self.incomingParcels[j].lastSeenOnCameraID:
                    timestamp = datetime.datetime.now()
                    if timestamp - self.incomingParcels[j].creationTime > \
                                   datetime.timedelta(seconds=self.secondsToIgnore):
                        if self.logger != None:
                            self.logger.info("Ignoring for too much elapsing time : "+ \
                                             self.incomingParcels[j].parcelID)
                        print("Ignoring for too much elapsing time : "+self.incomingParcels[j].parcelID)
                        self.incomingParcels.pop(j)
                        
            # Association des colis non tracker          
            for i in range(min(len(unassociateDetections2), len(self.incomingParcels))):
                resBoolean, area = self.trackerSpace.isInPrimeAssociationArea(unassociatedObjects[unassociateDetections2[i]][2])
                if resBoolean:
                    for j in range(len(self.incomingParcels)):
                        if self.incomingParcels[j].lastSeenOnCameraID == area:
                            self.trackedParcels.append(self.incomingParcels.pop(j))
                            if self.logger != None:
                                self.logger.info("Associating : "+ self.trackedParcels[-1].parcelID)
                            print("Associating : "+ self.trackedParcels[-1].parcelID)
                            if 'U0' in self.trackedParcels[-1].lastSeenOnCameraID:
                                if self.trackedParcels[-1].dimensionInit[2] != None:
                                    self.trackedParcels[-1].height = self.trackedParcels[-1].dimensionInit[2]
                                else:
                                    self.trackedParcels[-1].height = self.defaultHeight
                                    
                            self.trackedParcels[-1].isOutcoming = False
                            self.trackedParcels[-1].relativeBox = unassociatedObjects[unassociateDetections2[i]][2]
                            self.trackedParcels[-1].nextRelativeBox = unassociatedObjects[unassociateDetections2[i]][2]
                            self.trackedParcels[-1].lastSeenOnCameraID = self.unitName
                            self.trackedParcels[-1].numberOfTimesUndetected = 0
                            break;
                    self.parcelInfo = self.newParcel()

        else:
            for i in range(numObj):
                pass
            

    def newParcel(self): 
        ParcelInfo =  dict()
        ParcelInfo["Cam"] = ""
        ParcelInfo["zoneAsso"] = ""
        ParcelInfo["zoneTracking"] = ""
        ParcelInfo["fakeParcel"] = []
        return ParcelInfo
    
        
    def _manageExitingParcels(self):
        """
        Gère les paquets sortants ou enlevés.

        Args:
            numObj: le nombre d'objets detectes.
            objects: la liste des objets detectes.

        Returns:
            Les objets qui sont sortis ou retire du convoyeur.

        """
        exitingParcels = []
        removedParcels = []

        for i in range(len(self.trackedParcels)-1,-1,-1):
            if self.trackedParcels[i].numberOfTimesUndetected > self.numberOfTimeUndedectedThreshold:
                if self.logger != None:
                    self.logger.info("Removing for overtaking numberOfTimeUndedectedThreshold : "+  self.trackedParcels[i].parcelID)
                print("Removing for overtaking numberOfTimeUndedectedThreshold : "+  self.trackedParcels[i].parcelID)
                removedParcels.append(self.trackedParcels.pop(i))
                removedParcels[-1].isRemoved = True
                
            elif self.trackedParcels[i].numberOfTimesUndetected > self.numberOfTimeUndedectedThresholdPicked:
                if self.trackedParcels[i].isPickable:
                    xmin, xmax = self.trackedParcels[i].xPosition
                    xminLim, xmaxLim = self.trackedParcels[i].destinationPosition
                    if xminLim < xmin < xmaxLim or xminLim < xmax < xmaxLim :
                        if self.logger != None:
                            self.logger.info("Parcel sorted : "+  self.trackedParcels[i].parcelID)
                        print("Parcel sorted : "+  self.trackedParcels[i].parcelID)
                        removedParcels.append(self.trackedParcels.pop(i))
                        removedParcels[-1].isSorted = True

        for i in range(len(self.trackedParcels) - 1, -1, -1):
            xminLim, xmaxLim = self.trackedParcels[i].destinationPosition
            if self.trackedParcels[i].xPosition[1] >= self.xLimitParcel:
                if self.logger != None:
                    self.logger.info("Parcel final exiting : "+  self.trackedParcels[i].parcelID)
                print("Parcel final exiting : "+  self.trackedParcels[i].parcelID)
                exitingParcels.append(self.trackedParcels.pop(i))
                exitingParcels[-1].isOutcoming = False
                exitingParcels[-1].isExiting = True
                
        for i in range(len(self.trackedParcels) - 1, -1, -1):
            if self.trackedParcels[i].xPosition[1] > self.trackerSpace.xMaxLimit:
                if self.logger != None:
                    self.logger.info("Parcel exiting and outcoming : "+  self.trackedParcels[i].parcelID)
                print("Parcel exiting and outcoming : "+  self.trackedParcels[i].parcelID)
                exitingParcels.append(self.trackedParcels.pop(i))
                exitingParcels[-1].isOutcoming = True
                exitingParcels[-1].isExiting = True

        return exitingParcels, removedParcels
    
        
    def update(self, image, incomingParcels, cam):
        """
        Mets à jour tous les objets suivis et réalise le suivi.
        Seul methode du tracker utilisable.

        Args:
            numObj: le nombre d'objets detectes.
            objects: la liste des objets detectes.
            incomingParcels: Parcels venant de l'unité précédente.
            cam :  num camera realisant l'acquisition de l'image traitée

        Returns:
            Tous les objets suivis, sortants et retires.

        """
        t = time.perf_counter()
        # correction de la distortion des images
        if self.trackerSpace.doUndistortion:
            image = self.trackerSpace.undistortImage(image)
            
        # calcul des longueur et large de colis
        setParcelsWidthRef(self.trackedParcels, self.trackerSpace)
        
        # Détecte, filtre et prépare les objets pour le tracking.
        data = detectAndFilterParcels(self.parcelDetector, image, self.trackerSpace)

        # Filtre les parcels envoyés par l'unité précédente pour ne garder que ceux à venir.
        self._filterIncomingParcels(incomingParcels)

        # Gestion des parcels sortants ou enlevés.
        exitingParcels, removedParcels = self._manageExitingParcels()
        
        # mise à jour des positions relatives des colis
        self.p2pTracker.updatePositions(self.trackedParcels)

        # Réalise l'association optimale par IOU entre parcels et détection.
        # et utilisation du filtre de kalman
        unassociateDetections = self.detectionTracker.estimatePosition(self.trackedParcels, data.get('numObj'),
                                                                      data.get('objects'))
        # gestion des colis entrant et association
        self._manageIncomingAndNewParcels(data.get('numObj'), data.get('objects'), unassociateDetections)
        
        # met à jour la projection réelle 
        self.setRealPosition()
        
        # estime les positions relatives des colis les uns par rapport aux autres
        self.p2pTracker.estimatePosition(self.trackedParcels)
        
        #
        self.decisionFonction()

        print('Full timing update tracker : ', (time.perf_counter()-t)*1000)
   
        return {'parcels':self.trackedParcels + exitingParcels + removedParcels + self.incomingParcels,
                'objects': data.get('objects'), 
                'numObj': data.get('numObj')}
    

    def decisionFonction(self):
        
        for parcel in self.trackedParcels:
            decisionCondition = (not parcel.isTracked)
            if parcel.isTracked and parcel.widthRef[0] != 0 and parcel.widthRef[1] != 0:
                areaNew =  (parcel.xPosition[1] - parcel.xPosition[0]) * (parcel.yPosition[1] - parcel.yPosition[0])
                areaRef =  parcel.widthRef[0] * parcel.widthRef[1]
                areaCondition = (areaNew > (1 + self.areaConfidenceThreshold) * areaRef) or (areaNew < self.areaConfidenceThreshold * areaRef)
                decisionCondition = decisionCondition or areaCondition
                
            if decisionCondition and parcel.p2p_xyPosition != (0,0,0,0):
                parcel.xPosition = (parcel.p2p_xyPosition[1], parcel.p2p_xyPosition[3])
                parcel.yPosition = (parcel.p2p_xyPosition[0], parcel.p2p_xyPosition[2])
                parcel.relativeBox = self.trackerSpace.getImageCoordinates(parcel)
                if not parcel.isTracked:
                    parcel.nextRelativeBox = self.trackerSpace.getImageCoordinates(parcel)
                proj = self.trackerSpace.getBeltCoordinatesForImage(parcel.p2p_xyPosition)
                parcel.projectedBox = proj
                parcel.isTracked = False
                

    def setRealPosition(self):
        for parcel in self.trackedParcels + self.incomingParcels:
            coord = self.trackerSpace.getBeltCoordinates(parcel)
            parcel.xPosition = (coord[1], coord[3]) 
            parcel.yPosition = (coord[0], coord[2])
            proj = self.trackerSpace.getBeltCoordinatesForImage(coord)
            parcel.projectedBox = proj
            

    

  
