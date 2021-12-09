#!/usr/bin/env python3

from src.parcels.parcel import parcel
from src.utils.utils import (draw_bounding_box_on_image_array,
                            draw_bounding_box_on_image)


def drawParcelOnImageArray(parcel, image, *, thickness=4, displayString=True):
    """
    Dessine les éléments d'un Parcel sur l'image où il est détecté.

    Args:
        parcel: un objet Parcel a dessiné.
        image: l'image sur laquelle est dessiné le Parcel.
        thickness: l'épaisseur du trait de dessin en pixels.
    """
    ymin, xmin, ymax, xmax = parcel.relativeBox
    
    if displayString:
        draw_bounding_box_on_image_array(image, ymin, xmin, ymax, xmax, 
                                         parcel.trackingColor, thickness,
                                         parcel.getParcelDrawName(), True)
    else:
        draw_bounding_box_on_image_array(image, ymin, xmin, ymax, xmax,
                                         parcel.trackingColor, thickness,
                                         '', True)

