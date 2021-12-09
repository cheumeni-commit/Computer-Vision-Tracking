# -*- coding: utf-8 -*-
 
"""
    Classe Parcel.
"""


class Parcel():
    """
    Objet Parcel permet de mettre à jour l'état des Parcel tracker.

    Todo:
        Créer un module externe du Paquet parcel. 
    """

    def __init__(self, parcelID, parcelColor, creationTime, relativeBox = (0,0,0,0), 
                 nextRelativeBox= (0,0,0,0), parcelBarcode = None, 
                 destinationBay = None, postCode = None, destinationType = None, 
                 destinationPosition = (0,0), dimensionInit = (None, None, None),
                 isPickable = False):
        
        """Un paquet à suivre.
        
        Attributes:
        
            Attributs immuables crees a l'init :

            parcelID                ID UPU de l'objet
            type                    Type de colis, actuellement un seul type.
            creationTime            Timestamp de creation de l'objet.
            trackingColor           Couleur pour l'affichage visuel, couleur supportes : 
            
            Attributs immuables crees a l'init, non indispensable :

            parcelBarcode           Code barre du paquet. None si pas d'infos.
            destinationBay          Baie de destination. None si pas d'infos.
            postCode                Code Postal. None si pas d'infos.
            destinationType         Type de destination. None si pas d'infos.
            destinationPosition     Intervalle xmin, xmax reelle de la travee de destination. 
                                    None si pas d'infos.
            dimensionInit           Dimension de l'objet à l'init : longueur, largeur, hauteur. 
                                    None si pas d'infos.
            isPickable              Indique si l'objet est prenable par un operateur du systeme CARS.
                                    False si pas d'infos.

            Attributs de position mutable uniquement par le tracking :
            
            center                  Position (x,y) relative du centre du colis sur la camera courante.
            nextCenter              Position (x,y) predite relative du centre du colis sur la camera
                                    courante.
            relativeBox             Coordonnees relatives a l'image de la bounding box de l'objet.
            nextRelativeBox         Coordonnees predites relatives a l'image de la bounding box de
                                    l'objet.
            xPosition               Position (xmin, xmax) en millimetre du colis par rapport au plan de
                                    tri.
            yPosition               Position (ymin, ymax) en millimetre  du colis par rapport au plan de
                                    tri.
            projectedBox            Position reelle de l'objet projetée dans le referentiel image.

            Attributs de l'objet mutable uniquement par le tracking : 
            
            height                  Hauteur de l'objet.
            area                    Surface de l'objet.
            meanColorValue          Couleur moyenne dans la bounding box.

            Attributs de tracking modifiable par le tracking : 

            lastSeenOnCameraID      Id de la camera l'ayant detecté pour la derniere fois. 
            lastTimeDetected        Derniere timestamp ou l'objet est detecte.
            speed                   Vitesse.
            numberOfTimesUndetected   Nombre de fois non detecte. 
                                      (Modifiable par l'interpreteur seulement en cas de panne.)

            Attributs d'etat de l'objet modifiable uniquement par le tracking :

            isTracked               Indique si l'objet est suivi par detection ou non.
            isInterpolated          Indique si les positions ont ete detectees ou interpolees.
            isSorted                Indique si l'objet a ete trie, sorti dans la bonne travee.
            isRemoved               Indique si l'objet a ete sorti du convoyeur ou perdu.
            isOutcoming             Indique si l'objet est à venir dans un champ de camera.
            isExiting               Indique si l'objet est sorti du champ de la camera.

            Attributs d'informations de references
            
            heightRef                       Hauteur de reference calculee par le tracking.
            widthRef                        Longueur et largeur de reference calcule par le tracking.
            featureRef                      Caracteristique de reference.
            previousRelativeBox             Position du colis precedent pour le calcul de hauteur de
                                            reference.
            timeHoldingToEstimateHeight     Parametre pour le calcul de la hauteur de reference.

            Attributs d'informations pour le peer 2 peer tracker
            
            parcelsToParcelsDistance        La distance en millimetre entre le point xmin, ymin de ces
                                            parcels et
                                            Le point xmin,ymin de l'objet Parcel courant.
                                            La forme de stockage est sous forme de tuple (parcelID, dx,dy)     
            p2p_xyPosition                  Position reelle determinee par le peer 2 peer tracker.

        """
        
        ### Info global immuable :
        self.parcelID = parcelID #ID UPU
        self.type = 'Parcel' # un type de colis géré
        self.trackingColor = parcelColor
        self.creationTime = creationTime

        ### Info init immuable :
        self.parcelBarcode = parcelBarcode
        self.destinationBay = destinationBay
        self.postCode = postCode
        self.destinationType = destinationType
        self.destinationPosition = destinationPosition
        self.dimensionInit = dimensionInit
        self.isPickable = isPickable

        ### Info position
        self.relativeBox = relativeBox
        self.nextRelativeBox = nextRelativeBox
        self.center = ((relativeBox[3] + relativeBox[1]) / 2,\
                       (relativeBox[2] + relativeBox[0]) / 2)
        self.nextCenter = ((nextRelativeBox[3] + nextRelativeBox[1]) / 2,\
                           (nextRelativeBox[2] + nextRelativeBox[0]) / 2)


        self.xPosition = (0,0) 
        self.yPosition = (0,0) 

        self.projectedBox = (0, 0, 0, 0)

        ### Info objet 
        self.height = 0
        self.area = 0
        self.meanColorValue = (0,0,0)

        ### Info tracking 
        self.lastSeenOnCameraID = '' 
        self.numberOfTimesUndetected = 0
        self.lastTimeDetected = None
        self.speed = (0, 0) # vx, vy

        ### FLAGS :
        self.isTracked = False
        self.isInterpolated = False
        ## Le flags de position isSorted est inutilisé pour l'instant.
        self.isSorted = False
        self.isRemoved = False
        self.isOutcoming = False
        self.isExiting = False

        ### Info ref ###
        self.heightRef = 0
        self.widthRef = (0,0)
        self.featureRef = []
        self.previousRelativeBox = (0,0,0,0)
        self.timeHoldingToEstimateHeight = 0
        
        ### parcelsToParcelsDistance est une liste de maximum 3 parcels définissant
        #   la distance en millimetre entre le point xmin,ymin de ces parcels et
        #   le point xmin,ymin de l'objet Parcel courant.
        #   La forme de stockage est sous forme de tuple (parcelID,dx,dy). ###
        self.parcelsToParcelsDistance = []
        self.p2p_xyPosition = (0,0,0,0)
        

    def getColor(self):
        """
        Retourne la couleur de tracking du Parcel.

        Returns:
            trackingColor: couleur de tracking du Parcel.
        """
        return self.trackingColor
    
    def getRelativeBox(self):
        """
        Retourne la relativeBox du Parcel.
        Non utilisé et dangereux (retourne le pointeur).

        Returns:
            relativeBox: relativeBox du Parcel.
        """
        return self.relativeBox

    def getNextRelativeBox(self):
        """
        Retourne la nextRelativeBox du Parcel.
        Non utilisé et dangereux (retourne le pointeur).

        Returns:
            nextRelativeBox: nextRelativeBox du Parcel.
        """
        return self.nextRelativeBox

    def __str__(self):
        """
        Retourne la string du Parcel.

        Returns:
            La string du Parcel.
        """
        return self.type + ':' + self.parcelID

    def getParcelDrawName(self):
        """
        Retourne la string désignant le nom du Parcel.

        Returns:
            La string désignant le nom du Parcel.
        """
        s = self.parcelID.split('_')
        return [s[0] + '-' + s[-1]]
    
    def setWidthRef(self):
        
        x = self.xPosition[1] - self.xPosition[0]
        y = self.yPosition[1] - self.yPosition[0]
        self.widthRef = (x, y)
        

parcel = Parcel()
