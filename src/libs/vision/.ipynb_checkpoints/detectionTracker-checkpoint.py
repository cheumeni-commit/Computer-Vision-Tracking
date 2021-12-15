#!/usr/bin/env python3

from src.parcels.parcel import Parcel
from src.libs.vision.parcelAssociator import ParcelAssociator
from src.libs.vision.kalmanPredictor import KalmanFilterPredictor

      
class DetectionTracker():
    """
    Classe DetectionTracker permettant le suivi de colis par détection.

    Todo:
        Ajouter une liste de FantomParcels. Les Parcels fantôme répondent au besoin
        de créer des objets hors ud début de champ de vision et permettrait de recréer un
        objet réinsérer au milieu du convoyeur. Il permettrai également de gérer les fausses détections.
    """

    def __init__(self, fps, traceInfo = False):
        """
        Crée un objet DetectionTracker.

        Args:
            fps: vitesse d'acquisition du banc.
            traceInfo: booléen pour le traçage d'infos de debug.

        Attributes:        
            PA: le ParcelAssociator du tracker.
            KF: le KalmanFilterPredictor du tracker.
            traceInfo: booléen pour le traçage d'infos de debug.
            fps: vitesse d'acquisition du banc.
        """
        
        self.fps = fps
        self.traceInfo = traceInfo

        self.PA = ParcelAssociator()
        self.KF = KalmanFilterPredictor(self.fps)

    def estimatePosition(self, trackedParcels, numObj, objects):
              
        # Réalise l'association optimale par IOU entre parcels et détection.
        unassociateDetections = self.PA.associateWithIOU(trackedParcels, numObj, objects)
        
        # Prédit l'état futur de tous les parcels suivis.
        self.KF.updateStates(trackedParcels)

        return unassociateDetections
