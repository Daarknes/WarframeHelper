#!/usr/bin/env python
# -*- coding: utf-8 -*-
from builtins import Exception

import cv2
import pytesseract

import numpy as np
import math
import os
from relicrewards import instance
from core import wikiscaper, itemdata, constants
import functools
from core.itemdata import Category
import traceback
# import matplotlib.pyplot as plt


if os.path.isdir(instance.config["TESSERACT_PATH"]):
    _tess_path = os.path.join(instance.config["TESSERACT_PATH"], "tesseract.exe")
else:
    _tess_path = instance.config["TESSERACT_PATH"]

if not os.path.exists(_tess_path):
    raise Exception("No tesseract.exe at '" + instance.config["TESSERACT_PATH"] + "'")

pytesseract.pytesseract.tesseract_cmd = _tess_path
del _tess_path
# tesseract config options: https://www.pyimagesearch.com/2018/09/17/opencv-ocr-and-text-recognition-with-tesseract/
tessdata_dir = os.path.join(constants.res_loc(), "tessdata")
tess_config = r"--psm 6 --oem 1" #r'--tessdata-dir "{}" -l eng --psm 6 --oem 1'.format(tessdata_dir)


# Process pool for tesseract paralellization
_executor = None
_ocr_item_to_ducats = None
    

def init():
    # first try if pytessaract works at all
    _ = pytesseract.image_to_string(np.zeros((50, 250)))

    global _executor
    from concurrent.futures.process import ProcessPoolExecutor
    _executor = ProcessPoolExecutor(max_workers=4)
    
    _create_item_data()


def cleanup():
    _executor.shutdown()


def _create_item_data():
    item_data = itemdata.item_data()
    
    global _ocr_item_to_ducats
    _ocr_item_to_ducats = {"Forma Blueprint": None}

    for item_name, parts in wikiscaper.get_ducat_values(item_data[Category.RELICS]).items():
        for part_name, ducats in parts.items():
            full_name = item_name + " Prime " + part_name
            if (item_name+" Prime" in item_data[Category.WARFRAMES] or item_name+" Prime" in item_data[Category.ARCHWINGS]) and part_name != "Blueprint":
                full_name += " Blueprint"

            _ocr_item_to_ducats[full_name] = ducats


"""
reference values
"""
ref_width, ref_height = 2560, 1440
ref_ar = ref_height / float(ref_width)
# y-coordinate / height references
# part area
ref_ymin, ref_ymax = 720, 787 #473, 787
# item name area
ref_ymin_name, ref_ymax_name = 574, 646
# x-coordinate / width references
# width of a part
ref_part_width = 313
# spacing between two parts
ref_spacing = 10

# part name color (HSV)
ref_color_range = (np.array([13, 102, 170]), np.array([25, 120, 192]))


def _get_text_images(npimage):
    ar = npimage.shape[0] / float(npimage.shape[1])
    sw = (npimage.shape[1] * ar) / (ref_width * ref_ar)
    # height seems to be independent of resolution
    sh = npimage.shape[0] / float(ref_height)

    spacing = int(math.ceil(ref_spacing * sw))
    part_width = int(math.ceil(ref_part_width * sw))    
    ymin, ymax = int(ref_ymin * sh), int(ref_ymax * sh)
    
    # we can crop in x-coordinates because num_parts <= 4
    max_width = 4 * part_width + 3 * spacing
    xmin = (npimage.shape[1] - max_width) // 2

    hsv_image = cv2.cvtColor(npimage, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv_image[ymin:ymax, xmin:xmin+max_width], *ref_color_range)

    text_blocks = cv2.dilate(mask, np.ones((7, 9)), iterations=3)
    vsum = (np.sum(text_blocks, axis=0) > 0).astype(np.int)
    # just to be sure start and end exist
    vsum[0] = vsum[-1] = 0
    # finite differences
    vdiff = vsum[1:] - vsum[:-1]
    
    def gen():
        xbounds = zip((vdiff > 0).nonzero()[0], (vdiff < 0).nonzero()[0])
        for xmin, xmax in xbounds:
            part_image = 255 - mask[:, xmin:xmax]
            yield cv2.erode(part_image, np.ones((2, 2)), iterations=1)

    return gen()


def get_item_names(screenshot):
    """
    converts a screenshot to valid warframe item names and it's corresponding ducat value.
    @param screenshot: the screenshot as a PIL-Image or numpy-array
    """
    if _executor is None:
        raise Exception("warframe_ocr.init() was never called")

    try:
        screenshot = np.asarray(screenshot)
        tess_images = []
        
        for text_image in _get_text_images(screenshot):
            # embed the text image in a larger one with white background (tesseract needs a bit of space around the characters)
            tess_image = 255 * np.ones((text_image.shape[0] + 12, text_image.shape[1] + 12))
            tess_image[6:-6, 6:-6] = text_image
            tess_images.append(tess_image)

#         for i, tess_image in enumerate(tess_images):
#             plt.subplot(len(tess_images), 1, i+1)
#             plt.imshow(tess_image, cmap="gray")
#         plt.show()

        image_to_string = functools.partial(_image_to_string, name_list=list(_ocr_item_to_ducats.keys()))
        item_names = list(_executor.map(image_to_string, tess_images))
        return item_names, [_ocr_item_to_ducats.get(name) for name in item_names]
    except:
        print("[WF OCR] Error:")
        traceback.print_exc()
        return [], []


def _image_to_string(tess_image, name_list):
    item_name = pytesseract.image_to_string(tess_image, config=tess_config)

    # adjust to database
    lmin = 1e12
    best = item_name
 
    for db_name in name_list:
        ldist = levenshtein_distance(item_name, db_name, costs=(2, 2, 1))
        if ldist < lmin:
            lmin = ldist
            best = db_name
 
        if ldist == 0:
            lmin = 0
            break
     
    if lmin > 4:
        print("[WF OCR] '{}' is too far away from database (best match is '{}')".format(item_name, best))
        return "ERROR"
    else:
        return best


def levenshtein_distance(s, t, costs=(1, 1, 1)):
    """ 
        iterative_levenshtein(s, t) -> ldist (int)
        ldist is the Levenshtein distance between the strings s and t.
        
        costs: a tuple or a list with three integers (d, i, s) where
                d defines the costs for a deletion
                i defines the costs for an insertion and
                s defines the costs for a substitution
    """
    rows = len(s)+1
    cols = len(t)+1
    deletes, inserts, substitutes = costs
    
    # For all i and j, dist[i,j] will contain the Levenshtein distance between the first i characters of s and the first j characters of t
    dist = [[0 for _ in range(cols)] for _ in range(rows)]
    # source prefixes can be transformed into empty strings 
    # by deletions:
    for row in range(1, rows):
        dist[row][0] = row * deletes
    # target prefixes can be created from an empty source string
    # by inserting the characters
    for col in range(1, cols):
        dist[0][col] = col * inserts
        
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0
            else:
                cost = substitutes
            dist[row][col] = min(dist[row-1][col] + deletes,
                                 dist[row][col-1] + inserts,
                                 dist[row-1][col-1] + cost) # substitution    
 
    return dist[rows-1][cols-1]
    
