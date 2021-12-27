# -*- coding: utf-8 -*-
"""
    Classe ParcelIdManager.
"""

import datetime


class ParcelIdManager():
    """
    ParcelIdManager est la classe de génération des ID uniques des Parcel.
    Il génère également un timestamp de création pour l'objet Parcel.

    La gestion de la liste des ID générés est un peu déprécié mais pourrait
    servir en maintenance par exemple compter le nombre d'ID générés face au
    nombre d'ID triés.
    """
    
    def __init__(self, unitName):
        """
        Création d'un ParcelIdManager.
        
        Attributes:
            parcelIdList: liste des ID générés.
            resetDate: date de remise à zéro des ID pour ne pas exploser les ID.
            IdIterator: itérateur incrémenté à chaque génération pour composer un ID unique.
            unitName: nom de l'unité où le ParcelIdManager est instancié.

        Args:
            unitName: nom de l'unité où le ParcelIdManager est instancié. Le
            nom de l'unité est important car utilisé pour générer un ID unique.
        """
        self.parcelIdList = dict()
        self._resetDate = datetime.datetime.now().strftime("%Y-%m-%d")
        self.IdIterator = 0
        self.unitName = unitName
        

    def getParcelIdList(self):
        """
        Retourne la liste des parcelId générés.

        Returns:
           La liste des parcelId générés.
        """
        return [*self.parcelIdList]
    

    def deleteManagedId(self, parcelID):
        """
        Supprime un ID de la liste des ID générés.

        Args:
            parcelID: l'id généré d'un parcel.

        Returns:
            un booléen donnant l'information si l'ID a été supprimé ou non.
        """
        return not self.parcelIdList.pop(parcelID, None)

    def _addNewId(self, parcelID):
        """
        Ajoute un ID de la liste des ID générés.

        Args:
            parcelID: l'id généré d'un parcel.

        Returns:
            un booléen donnant l'information si l'ID a été bien créé.
        """

        self.parcelIdList[parcelID] = 0
        return parcelID in self.parcelIdList

    def parcelIdGenerator(self):
        """
        Génère un ID unique et un timestamp pour un objet Parcel.

        Returns:
            parcelID: un ID unique pour Parcel.
            timestamp: un timestamp de création.
        """
        currentDay = datetime.datetime.now().strftime("%Y-%m-%d")
        if currentDay != self._resetDate:
            self.IdIterator = 1
            self._resetDate = currentDay
        else:
            self.IdIterator += 1
            
        timestamp = datetime.datetime.now()
        parcelID = self.unitName + '_' + timestamp.strftime("%Y%m%d-%H%M%S%f") \
                    + '_' + '{:09}'.format(self.IdIterator)
        
        self._addNewId(parcelID)
        return parcelID, timestamp
