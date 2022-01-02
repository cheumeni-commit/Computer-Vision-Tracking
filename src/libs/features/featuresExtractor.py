#!/usr/bin/env python3


def setParcelsWidthRef(parcels, trackerSpace):
    for parcel in parcels:
        a = (parcel.relativeBox[1] < trackerSpace.imageCenter[0])
        b = (parcel.relativeBox[3] > trackerSpace.imageCenter[0])
        if a and b :
            parcel.setWidthRef() 
