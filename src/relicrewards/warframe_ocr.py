from builtins import Exception

import cv2
import pytesseract

import numpy as np
import math
from concurrent.futures.process import ProcessPoolExecutor
import os
from relicrewards import instance
import matplotlib
from core import wikiscaper, itemdata
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
# y-coordinate / height references
# part area (currently not in use)
ref_ymin_part, ref_ymax_part = 244, 654
# possible player names / checkmark area (if all 4 players selected the same item)
ref_ymin_players, ref_ymax_players = 418, 606
# item name area
ref_ymin_name, ref_ymax_name = 574, 646

# x-coordinate / width references
# width of a part
ref_part_width = 559
# spacing between two parts
ref_spacing = 17

# Process pool for tesseract paralellization
_executor = None
_ocr_item_to_ducats = None

def init():
    # first try if pytessaract works at all
    _ = pytesseract.image_to_string(np.zeros((50, 250)))

    global _executor
    _executor = ProcessPoolExecutor(max_workers=4)
    # try using pytessaract in parallel
    _ = list(_executor.map(pytesseract.image_to_string, (np.zeros((50, 250)) for _ in range(4))))

    update_item_data()

def cleanup():
    _executor.shutdown()

#@benchmark
def _get_name_boxes(npimage):
    ar = npimage.shape[0] / float(npimage.shape[1])
    sw = (npimage.shape[1] * ar) / (ref_width * ref_ar)
    # height seems to be independent of resolution
    sh = npimage.shape[0] / float(ref_height)

    spacing = int(math.ceil(ref_spacing * sw))
    part_width = int(math.ceil(ref_part_width * sw))
    ymin_players, ymax_players = int(ref_ymin_players * sh), int(ref_ymax_players * sh)
    
    # we can crop in x-coordinates because num_players <= 4
    max_width = 4 * part_width + 3 * spacing
    xmin = (npimage.shape[1] - max_width) // 2
    num_players = _get_num_players(npimage[ymin_players:ymax_players, xmin:xmin+max_width], sw, sh)
#     print("[WF OCR] found {} players".format(num_players))
    
    ymin_name, ymax_name = int(ref_ymin_name * sh), int(ref_ymax_name * sh)
    x = max(int(2 * sw), 1) + (npimage.shape[1] - (num_players * part_width + (num_players - 1) * spacing)) // 2
    xmin_off, xmax_off = max(int(7 * sw), 2), max(int(8 * sw), 2)
    
    boxes = []
    for _ in range(num_players):
        boxes.append((x + xmin_off, ymin_name, x + part_width - xmax_off, ymax_name))
        x += part_width + spacing
    
    return boxes

ref_checkmark_image = cv2.imread(os.path.join("..", "res", "checkmark.png"), 0)
#@benchmark
def _get_num_players(parts_image, sw, sh):
    players_image_gray = cv2.cvtColor(parts_image, cv2.COLOR_RGB2GRAY)
    checkmark_image = cv2.resize(ref_checkmark_image, (int(ref_checkmark_image.shape[1] * sw), int(ref_checkmark_image.shape[0] * sh)))
    results = cv2.matchTemplate(players_image_gray, checkmark_image, cv2.TM_SQDIFF_NORMED)
    
#     plt.subplot(2, 2, 1)
#     plt.imshow(players_image_gray, cmap="gray")
#     plt.subplot(2, 2, 2)
#     plt.imshow(checkmark_image, cmap="gray")
#     plt.subplot(2, 2, 3)
#     plt.imshow(results, cmap="gray")
#     plt.subplot(2, 2, 4)
#     plt.imshow(results, cmap="gray")
    
    num_players = 1
    for _ in range(4):
        y, x = np.unravel_index(np.argmin(results), results.shape)
        # when the next match is not good enough there probably aren't more players
        if (results[y, x] > CHECKMARK_MATCH_THRESHHOLD):
            break
        num_players += 1
        results[y-8:y+8, x-8:x+8] = 1
        
#         plt.plot(x, y, marker="o", markersize=2, color="red")
#     plt.show()
    
    return num_players

bronze_min = np.array([30 / 360, 0.54, 0.46])
bronze_max = np.array([34 / 360, 0.83, 0.64])
silver_min = np.array([0, 0, 0.52])
silver_max = np.array([2 / 360, 0.02, 0.85])
gold_min = np.array([45 / 360, 0.51, 0.51])
gold_max = np.array([51 / 360, 0.56, 0.85])

def _filter_gradient(part_image, hsv_min, hsv_max):
    hsv_image = matplotlib.colors.rgb_to_hsv(part_image / 255)
    
    smaller_ind = np.any(hsv_image < hsv_min, axis=2)
    larger_ind = np.any(hsv_image > hsv_max, axis=2)

    image = np.ones(hsv_image.shape[:2])
    image[smaller_ind | larger_ind] = 0
    
    return image
    
def _get_text_image(part_image):
    image_bronze = _filter_gradient(part_image, bronze_min, bronze_max)
    rowsum_bronze = np.sum(image_bronze, axis=1)
    
    image_silver = _filter_gradient(part_image, silver_min, silver_max)
    rowsum_silver = np.sum(image_silver, axis=1)
    
    image_gold = _filter_gradient(part_image, gold_min, gold_max)
    rowsum_gold = np.sum(image_gold, axis=1)
    
    # pick the best of the three
    rowsums = (rowsum_bronze, rowsum_silver, rowsum_gold)
    chosen_ind = np.argmax([np.max(rowsum) for rowsum in rowsums])
    rowsum = rowsums[chosen_ind]
    image = (image_bronze, image_silver, image_gold)[chosen_ind]
    
    s_cutoff = 0.2
    text_y_ind = np.where(rowsum > rowsum.max() * s_cutoff)[0]
    # crop in y-direction
    image = image[text_y_ind[0]:text_y_ind[-1] + 1, :]
    colsum = np.sum(image, axis=0)
    text_x_ind = np.where(colsum > 0)[0]
    image = image[:, text_x_ind[0]:text_x_ind[-1] + 1]
    
    # invert colors (so that text is black and the rest white)
    image = 255 * (1 - image)
    
#     plt.subplot(3, 3, 1)
#     plt.imshow(part_image)
#     plt.subplot(3, 3, 2)
#     plt.title("rowsums")
#     plt.plot(rowsum_bronze, label="bronze")
#     plt.plot(rowsum_silver, label="silver")
#     plt.plot(rowsum_gold, label="gold")
#     plt.legend()
#     plt.subplot(3, 3, 3)
#     plt.title("colsum (of the chosen image)")
#     plt.plot(colsum)
#        
#     plt.subplot(3, 3, 4)
#     plt.imshow(image_bronze, cmap="gray")
#     plt.subplot(3, 3, 5)
#     plt.imshow(image_silver, cmap="gray")
#     plt.subplot(3, 3, 6)
#     plt.imshow(image_gold, cmap="gray")
#       
#     plt.subplot(3, 3, 8)
#     plt.imshow(image, cmap="gray")
#       
#     plt.show()
    
    return image

# def _filter_peaks(image, exp=10):
#     return ((1 - (1 - image / 255.0)**exp) * 255).astype(np.uint8)


def update_item_data():
    item_data = itemdata.item_data()
    
    global _ocr_item_to_ducats
    _ocr_item_to_ducats = {"FORMA BLUEPRINT": None}

    for item_name, parts in wikiscaper.get_ducat_values(item_data[Category.RELICS]).items():
        for part_name, ducats in parts.items():
            full_name = item_name + " Prime " + part_name
            if item_name+" Prime" in item_data[Category.WARFRAMES] and part_name != "Blueprint":
                full_name += " Blueprint"

            _ocr_item_to_ducats[full_name.upper()] = ducats


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
        
        for x1, y1, x2, y2 in _get_name_boxes(screenshot):
            part_image = screenshot[y1:y2, x1:x2]
            
            text_image = _get_text_image(part_image)
            # embed the text image in a larger one with white background (tesseract needs a bit of space around the characters)
            h, w = text_image.shape
            tess_image = 255 * np.ones((h + 12, w + 12))
            tess_image[6:6+h, 6:6+w] = text_image
            
            tess_images.append(tess_image)
            
#             plt.subplot(2, 1, 1)
#             plt.imshow(part_image)
#             plt.subplot(2, 1, 2)
#             plt.imshow(tess_image, cmap="gray")
#             plt.show()

        image_to_string = functools.partial(_image_to_string, name_list=list(_ocr_item_to_ducats.keys()))
        item_names = list(_executor.map(image_to_string, tess_images))
        return item_names, [_ocr_item_to_ducats.get(name) for name in item_names]
    except:
        print("[WF OCR] Error:")
        traceback.print_exc()
        return [], []


def _image_to_string(tess_image, name_list):
    item_name = pytesseract.image_to_string(tess_image)

    # adjust to database
    lmin = 1e12
    best = item_name
 
    for db_name in name_list:
        ldist = levenshtein_distance(item_name, db_name, costs=(2, 2, 1))
        if ldist < lmin:
            lmin = ldist
            best = db_name
 
        if ldist == 0:
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
    
