#!/usr/bin/env python3


def setParcelsWidthRef(parcels, trackerSpace):
    for parcel in parcels:
        if parcel.relativeBox[1] < trackerSpace.imageCenter[0] \
           and parcel.relativeBox[3] > trackerSpace.imageCenter[0]:
            parcel.setWidthRef() 
