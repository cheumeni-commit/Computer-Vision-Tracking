#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

    
def filterPredictions(numObj, objects, trackerSpace):
    """
    Filtre les détections d'objets qui ne sont pas sur le tapis.

    Args:
        numObj: le nombre d'objets detectes.
        objects: la liste des objets detectes.

    Returns:
        La liste des objets detectes ayant passe le filtre et la taille de cette liste.
    """
    filteredObjects = []
    for i in range(numObj):
        if trackerSpace.isInBeltBoundaries(objects[i][2]):
            filteredObjects.append(objects[i])
            
    return {'numObj':len(filteredObjects), 'objects':filteredObjects}


def detectAndFilterParcels(parcelDetector, image, beltBoundaries, logger, cam, incomingParcels):
    """
    Détecte et prépare les objets détecté pour le tracking.

    Args:
        numObj: le nombre d'objets detectes.
        objects: la liste des objets detectes.

    Returns:
        La liste trie dans le sens des xmax croissants des objets detectes
        ayant passe le filtre et la taille de cette liste.
    """
        
    numObj, objects = parcelDetector.run_inference_for_frame(image)
    # trace logger
    if len(objects) !=0:
        for i in range(len(objects)):
            logger.info("--- Score detection object par NR:{} cam: {} ---".format(objects[i][1], cam))
           #print("--- Score detection object par NR:{} cam: {} ---".format(objects[i][1], cam))
    else:
        logger.info("--- nombre de detection NR:{} ---".format(len(objects)))
       #print("--- nombre de detection NR:{} ---".format(len(objects)))

    # filtre les détections qui ne sont sur le tapis
    data = filterPredictions(numObj, objects, beltBoundaries)
    # trie les colis le front avant x_max
    data['objects'].sort(key=lambda x: x[2][3], reverse=False) #Fait tenir debout tout le tracking.
    
    return data
