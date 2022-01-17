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
    filteredObjects = [objects[i] for i, _ in enumerate(numObj) if trackerSpace.isInBeltBoundaries(objects[i][2])]
            
    return {'numObj':len(filteredObjects), 'objects':filteredObjects}


def detectAndFilterParcels(parcelDetector, image, beltBoundaries):
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

    # filtre les détections qui ne sont sur le tapis
    data = filterPredictions(numObj, objects, beltBoundaries)
    # trie les colis par le front avant x_max
    data.get('objects').sort(key=lambda x: x[2][3], reverse=False) #Fait tenir debout tout le tracking.
    
    return data
