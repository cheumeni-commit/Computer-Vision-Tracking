#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)


def filterPredictions(numObj, objects, trackerSpace):
       
    filteredObjects = []
    for i in range(numObj):
        if trackerSpace.isInBeltBoundaries(objects[i][2]):
            filteredObjects.append(objects[i])
    return len(filteredObjects), filteredObjects


def detectAndFilterParcels(parcelDetector, image, trackerSpace):
    """
    """

    numObj, objects = parcelDetector.run_inference_for_frame(image)
    
    ### trace logger
    if len(objects) !=0:
       for i in range(len(objects)):
           # print("--- Score detection object par NR:{} cam: {} ---".format(objects[i][1], 1))
           continue
    else:
       print("--- nombre de detection NR:{} ---".format(len(objects)))

    # filtre les détections qui ne sont sur le tapis
    numFilteredObj, filteredObjects = filterPredictions(numObj, objects, trackerSpace)
    print("----------- nombre d'element detecté sur le convoyeur : {} ---".format(numFilteredObj))
    # trie les colis par le front avant x_max
    filteredObjects.sort(key=lambda x: x[2][3], reverse=False) #Fait tenir debout tout le tracking. 
    return numFilteredObj, filteredObjects