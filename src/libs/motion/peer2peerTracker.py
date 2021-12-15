#!/usr/bin/env python3
import numpy as np

from src.parcels.parcel import Parcel
from src.parcelSpace import TrackerSpace


def getTrackedParcelByID(parcels, parcelID):
    for parcel in parcels:
        if parcel.parcelID == parcelID:
            return parcel
    return None


class Peer2peerTracker():

    def __init__(self):
        self.maxParcels = 3
        self.minParcels = 2

    def updatePositions(self, parcels):
        for i in range(len(parcels)):
            dists = []
            for j in range(len(parcels)):
                if parcels[i].isTracked:
                    dists.append((j,np.linalg.norm([parcels[i].xPosition[0]-parcels[j].xPosition[0], parcels[i].yPosition[0]-parcels[j].yPosition[0]])))
         
            dists = sorted(dists, key=lambda x: x[1])
            parcelsToParcelsDistance = [] 
                     
            for k in range(min(len(dists), self.maxParcels)):
                pID = parcels[dists[k][0]].parcelID
                deltaX = (parcels[i].xPosition[0] - parcels[dists[k][0]].xPosition[0])
                deltaY = (parcels[i].yPosition[0] - parcels[dists[k][0]].yPosition[0])
                parcelsToParcelsDistance.append((pID, deltaX, deltaY))
            parcels[i].parcelsToParcelsDistance = parcelsToParcelsDistance

    def estimatePosition(self, parcels):
                     
        for parcel in parcels:
            if parcel.widthRef[0] != 0 and parcel.widthRef[1] != 0:
                xs = []
                ys = []
                for p2pd in parcel.parcelsToParcelsDistance:
                    parcel2 = getTrackedParcelByID(parcels, p2pd[0])
                    if parcel2 != None:
                        if parcel2.isTracked:
                            xs.append(parcel2.xPosition[0] + p2pd[1])
                            ys.append(parcel2.yPosition[0] + p2pd[2])
                if len(xs) >= self.minParcels:
                    meanX = float(np.mean(np.array(xs)))
                    meanY = float(np.mean(np.array(ys)))
                    parcel.p2p_xyPosition = (meanY, meanX, meanY + parcel.widthRef[1], meanX + parcel.widthRef[0])
                else:
                    parcel.p2p_xyPosition = (0,0,0,0)
            else:
                parcel.p2p_xyPosition = (0,0,0,0)
