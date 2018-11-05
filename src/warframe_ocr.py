from builtins import Exception
import json
import sys
import traceback

import cv2
import pytesseract

from decorators import benchmark
import matplotlib.pyplot as plt
import numpy as np
import math
import time
import multiprocessing
from concurrent.futures.process import ProcessPoolExecutor


pytesseract.pytesseract.tesseract_cmd = r'E:\Tesseract\tesseract.exe'


# threshhold for the checkbox pattern matching which evaluates the number of players
CHECKMARK_MATCH_THRESHHOLD = 0.15
# truncates a part image when the difference between part image and font color is greater than this value
COLOR_TRUNCATE_THRESHHOLD = 10
# how much larger can the difference between two font colors be to be chosen as the upper most line
COLOR_SUM_THRESHHOLD_MULTI = 1.25


"""
reference values
"""
ref_width, ref_height = 2560, 1440
ref_ar = ref_height / float(ref_width)
# ref_ymin is the y-coordinate where the player names can begin if all 4 players selected the same item
ref_ymin, ref_ymax = 440, 654
#ref_ymin, ref_ymax = 244, 654
ref_part_width = 559
ref_spacing = 17

#@benchmark
def _get_part_boxes(npimage):
    ar = npimage.shape[0] / float(npimage.shape[1])
    sw = (npimage.shape[1] * ar) / (ref_width * ref_ar)
    # height seems to be independent of resolution
    sh = npimage.shape[0] / float(ref_height)
    ymin, ymax = int(ref_ymin * sh), int(ref_ymax * sh)

    spacing = int(math.ceil(ref_spacing * sw))
    part_width = int(math.ceil(ref_part_width * sw))
    
    num_players = _get_num_players(npimage[ymin:ymax], sw, sh)
#     print("[WF OCR] found {} players".format(num_players))
    
    boxes = []
    x = max(int(2 * sw), 1) + (npimage.shape[1] - (num_players * part_width + (num_players - 1) * spacing)) // 2
    xmin_off, xmax_off = max(int(7 * sw), 2), max(int(8 * sw), 2)
    ymin_off, ymax_off = max(int(3 * sh), 2), max(int(7 * sh), 2)

    for _ in range(num_players):
        boxes.append((x + xmin_off, ymin + ymin_off, x + part_width - xmax_off, ymax - ymax_off))
        x += part_width + spacing
    
    return boxes

ref_checkmark_image = cv2.imread("checkmark.png", 0)
#@benchmark
def _get_num_players(parts_image, sw, sh):
    parts_image_gray = cv2.cvtColor(parts_image, cv2.COLOR_RGB2GRAY)
    checkmark_image = cv2.resize(ref_checkmark_image, (int(ref_checkmark_image.shape[1] * sw), int(ref_checkmark_image.shape[0] * sh)))
    results = cv2.matchTemplate(parts_image_gray, checkmark_image, cv2.TM_SQDIFF_NORMED)
    
    num_players = 1
    for _ in range(4):
        y, x = np.unravel_index(np.argmin(results), results.shape)
        # when the next match is not good enough there probably aren't more players
        if (results[y, x] > CHECKMARK_MATCH_THRESHHOLD):
            break
        num_players += 1
        results[y-8:y+8, x-8:x+8] = 1
        
#         plt.plot(x, y, marker="o", markersize=1, color="red")
#     
#     plt.subplot(2, 2, 1)
#     plt.imshow(parts_image_gray, cmap="gray")
#     plt.subplot(2, 2, 2)
#     plt.imshow(checkmark_image, cmap="gray")
#     plt.subplot(2, 2, 3)
#     plt.imshow(results, cmap="gray")
#     
#     plt.subplot(2, 2, 4)
#     plt.imshow(results, cmap="gray")
#     
#     plt.show()
    
    return num_players


color_bronze = np.array([157, 116, 69])[None, None, :]
color_silver = np.array([211, 211, 211])[None, None, :]
color_gold = np.array([211, 187, 99])[None, None, :]

#@benchmark
def _get_name_start_height(part_image):
    image_bronze = np.sqrt(np.sum((part_image - color_bronze)**2, axis=2))
    image_bronze[image_bronze > COLOR_TRUNCATE_THRESHHOLD] = 255
    rowsum_bronze = np.sum(image_bronze, axis=1)
    
    image_silver = np.sqrt(np.sum((part_image - color_silver)**2, axis=2))
    image_silver[image_silver > COLOR_TRUNCATE_THRESHHOLD] = 255
    rowsum_silver = np.sum(image_silver, axis=1)
    
    image_gold = np.sqrt(np.sum((part_image - color_gold)**2, axis=2))
    image_gold[image_gold > COLOR_TRUNCATE_THRESHHOLD] = 255
    rowsum_gold = np.sum(image_gold, axis=1)
    
    rowsums = (rowsum_bronze, rowsum_silver, rowsum_gold)
    chosen_ind = np.argmin([np.min(rowsum) for rowsum in rowsums])
    rowsum = rowsums[chosen_ind]
    
#     print("[WF OCR] Detected a", ("bronze", "silver", "gold")[chosen_ind], " item name")
    
#     plt.subplot(2, 3, 1)
#     plt.imshow(part_image)
#     plt.subplot(2, 3, 2)
#     plt.plot(rowsum_bronze)
#     plt.plot(rowsum_silver)
#     plt.plot(rowsum_gold)
#     
#     plt.subplot(2, 3, 4)
#     plt.imshow(image_bronze, cmap="gray")
#     plt.subplot(2, 3, 5)
#     plt.imshow(image_silver, cmap="gray")
#     plt.subplot(2, 3, 6)
#     plt.imshow(image_gold, cmap="gray")
#     plt.show()
    
    return np.where(rowsum < rowsum.min() * COLOR_SUM_THRESHHOLD_MULTI)[0][0] - 6

def _filter_peaks(image, exp=10):
    return ((1 - (1 - image / 255.0)**exp) * 255).astype(np.uint8)

#@benchmark
def get_item_names(screenshot):
    """
    converts a screenshot to valid warframe item names.
    @param screenshot: the screenshot as a PIL-Image or numpy-array
    """
    try:
        screenshot = np.asarray(screenshot)
        
        tess_images = []
        
        for x1, y1, x2, y2 in _get_part_boxes(screenshot):
            part_image = screenshot[y1:y2, x1:x2]
            ystart_ind = _get_name_start_height(part_image)
            
            parts_image_gray = cv2.cvtColor(part_image[ystart_ind:, :], cv2.COLOR_RGB2GRAY)
            parts_image_gray = _filter_peaks(parts_image_gray, exp=0.2)
            # cutoff (also invert the colors)
            cutoff_ind = parts_image_gray < 8
            parts_image_gray[cutoff_ind] = 255
            parts_image_gray[~cutoff_ind] = 0 # np.minimum(parts_image_gray[~cutoff_ind].astype(np.int16) * 2, 255).astype(np.uint8)
            
            h, w = parts_image_gray.shape
            # embed the image in a larger one with white background (tesseract needs a bit of space around the characters)
            tess_image = 255 * np.ones((h + 20, w + 20))
            tess_image[10:10+h, 10:10+w] = parts_image_gray
            tess_images.append(tess_image)
            
#             plt.subplot(3, 1, 1)
#             plt.imshow(screenshot[y1:y2, x1:x2])
#             plt.subplot(3, 1, 2)
#             plt.imshow(part_image[ystart_ind:, :], cmap="gray")
#             plt.subplot(3, 1, 3)
#             plt.imshow(tess_image, cmap="gray")
#             plt.show()
        
        num_workers = min(len(tess_images), multiprocessing.cpu_count())
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            item_names = executor.map(pytesseract.image_to_string, tess_images)
            item_names = executor.map(_adjust_to_database, item_names)
   
        return list(item_names)
    except Exception:
        print("[WF OCR] Error:\n", traceback.print_exc(file=sys.stdout))
        return []


with open("item_data.json", "r", encoding="utf-8") as f:
    item_database = json.load(f)

#@benchmark 
def _adjust_to_database(name):
    lmin = 1e12
    best = name

    for db_name in item_database:
        ldist = levenshtein_distance(name, db_name, costs=(2, 2, 1))
        if ldist < lmin:
            lmin = ldist
            best = db_name

        if ldist == 0:
            break
    
    if lmin > len(name):
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
    dist = [[0 for x in range(cols)] for x in range(rows)]
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
    
