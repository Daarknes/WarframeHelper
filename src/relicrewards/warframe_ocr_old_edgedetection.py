from builtins import Exception

import cv2
import pytesseract

import numpy as np
import json
from decorators import benchmark
import time
import traceback
import sys

import matplotlib.pyplot as plt


pytesseract.pytesseract.tesseract_cmd = r'E:\Tesseract\tesseract.exe'



# threshhold for the horizontal line detection
THRESHHOLD_HOR = 0.35

# for vertical line recognition we only take the bottom most X-percent of the image
VERT_PERC = 0.23
# threshhold for the vertical line detection
THRESHHOLD_VER = 0.55

COLOR_TRUNCATE_THRESHHOLD = 10
COLOR_SUM_THRESHHOLD_MULTI = 0.75



def filter_peaks(image, exp=10):
    return ((1 - (1 - image / 255.0)**exp) * 255).astype(np.uint8)


@benchmark
def get_part_rectangles(screenshot_grayscale):
    image = filter_peaks(screenshot_grayscale, exp=10)

    plt.subplot(2, 1, 1)
    plt.imshow(image, cmap="gray")
    plt.subplot(2, 1, 2)
    plt.imshow(filter_peaks(screenshot_grayscale, exp=4), cmap="gray")
    plt.show()

    # search for the two horizontal 'lines' encapsulating the items
    sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
    rowsum = np.abs(sobely.sum(axis=1))
    max_ind_y = np.where(rowsum > THRESHHOLD_HOR * rowsum.max())[0]
    ymin_ind, ymax_ind = max_ind_y[0] + 10, max_ind_y[-1] - 10
    
    plt.subplot(2, 2, 1)
    plt.imshow(sobely, cmap="gray")
    plt.subplot(2, 2, 2)
    plt.plot(rowsum, range(0, -len(rowsum), -1))
    plt.axvline(THRESHHOLD_HOR * rowsum.max())
    plt.subplot(2, 2, 3)
    plt.imshow(screenshot_grayscale[ymin_ind:ymax_ind, :], cmap="gray")
    plt.tight_layout()
    plt.show()
    
#    data = image[ymin_ind:ymax_ind, :] / 255.0
#    sobelx = 0.5 * (np.abs(cv2.Sobel(data, cv2.CV_64F, 1, 0, ksize=3)) + np.abs(cv2.Sobel(-data, cv2.CV_64F, 1, 0, ksize=3)))
    sobelx = cv2.Sobel(image[ymin_ind:ymax_ind, :], cv2.CV_64F, 1, 0, ksize=3)
    # take the bottom most X-percent of the sobeled image
    start = int(sobelx.shape[0] * (1 - VERT_PERC))
    colsum = np.abs(sobelx[start:].sum(axis=0))
    # use symmetry to make the results slightly better
    colsum += colsum[::-1]
    max_ind_x = np.where(colsum > THRESHHOLD_VER * colsum.max())[0]
    
    plt.subplot(2, 1, 1)
    plt.imshow(sobelx[start:], cmap="gray")
    plt.subplot(2, 1, 2)
    plt.plot(colsum)
    plt.axhline(THRESHHOLD_VER * colsum.max())
    plt.show()
    
    def next_valid_index():
        last_index = -100
        for i in max_ind_x:
            # distance between two maxima (lines) should be at least 8 pixels
            if i - last_index > 8:
                last_index = i
                yield i
    
    part_rects = []
    index_it = next_valid_index()

    try:
        while True:
            xmin_ind = next(index_it) + 4
            xmax_ind = next(index_it) - 4
            part_rects.append((xmin_ind, ymin_ind, xmax_ind, ymax_ind))
    except StopIteration:
        pass
     
#     for i, rect in enumerate(name_rects):
#         plt.subplot(2, len(name_rects), i+1)
#         plt.imshow(screenshot[rect[1]:rect[3], rect[0]:rect[2]], cmap="gray")
#         plt.subplot(2, len(name_rects), len(name_rects) + i+1)
#         plt.imshow(image[rect[1]:rect[3], rect[0]:rect[2]], cmap="gray")
#     plt.show()

    return part_rects



color_bronze = np.array([157, 116, 69])[None, None, :]
color_silver = np.array([211, 211, 211])[None, None, :]
color_gold = np.array([200, 184, 122])[None, None, :]

@benchmark
def get_name_start_height(part_image):
    ystart_offset = int((1 - VERT_PERC) * part_image.shape[0])
    part_image = part_image[ystart_offset:]
    image_bronze = np.sqrt(np.sum((part_image - color_bronze)**2, axis=2))
    image_bronze[image_bronze > COLOR_TRUNCATE_THRESHHOLD] = 0
    rowsum_bronze = np.sum(image_bronze, axis=1)
    
    image_silver = np.sqrt(np.sum((part_image - color_silver)**2, axis=2))
    image_silver[image_silver > COLOR_TRUNCATE_THRESHHOLD] = 0
    rowsum_silver = np.sum(image_silver, axis=1)
    
    image_gold = np.sqrt(np.sum((part_image - color_gold)**2, axis=2))
    image_gold[image_gold > COLOR_TRUNCATE_THRESHHOLD] = 0
    rowsum_gold = np.sum(image_gold, axis=1)
    
    rowsums = (rowsum_bronze, rowsum_silver, rowsum_gold)
    rowsum = rowsums[np.argmax([np.max(rowsum) for rowsum in rowsums])]
    
#     plt.subplot(1, 4, 1)
#     plt.imshow(part_image)
#     plt.subplot(1, 4, 2)
#     plt.imshow(image_bronze, cmap="gray")
#     plt.subplot(1, 4, 3)
#     plt.imshow(image_silver, cmap="gray")
#     plt.subplot(1, 4, 4)
#     plt.imshow(image_gold, cmap="gray")
#     plt.show()
    
    return ystart_offset + np.where(rowsum > rowsum.max() * COLOR_SUM_THRESHHOLD_MULTI)[0][0] - 8

@benchmark
def get_item_names(screenshot):
    """
    converts a screenschot to valid warframe item names.
    @param screenshot: the screenshot as a PIL-Image
    """
    try:
        x, y = screenshot.size[0] * 0.03, screenshot.size[1] * 0.08
        screenshot = np.asarray(screenshot.crop((x, y, screenshot.size[0] - x, screenshot.size[1] // 2)))
        screenshot_grayscale = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
        
        part_rects = get_part_rectangles(screenshot_grayscale)
        item_names = []
        
        for xmin_ind, ymin_ind, xmax_ind, ymax_ind in part_rects:
            part_image = screenshot[ymin_ind:ymax_ind, xmin_ind:xmax_ind]
            ystart_ind = get_name_start_height(part_image)
            
            image = screenshot_grayscale[ymin_ind+ystart_ind:ymax_ind, xmin_ind:xmax_ind]
            image = filter_peaks(image, exp=0.2)
            
    #         plt.subplot(2, 1, 1)
    #         plt.imshow(part_image[ystart_ind:, :], cmap="gray")
    #         plt.subplot(2, 1, 2)
    #         plt.imshow(image, cmap="gray")
    #         plt.show()
            
            start = time.clock()
            item_name = pytesseract.image_to_string(image)
            duration = (time.clock() - start) * 1000.0
            print("benchmark for 'pytesseract.image_to_string': {0:.3f} ms".format(duration))
            
            item_name = adjust_to_database(item_name)
            item_names.append(item_name)
        
        return item_names
    except Exception:
        print("[WF OCR] Error:\n", traceback.print_exc(file=sys.stdout))
        return []


with open("item_data.json", "r", encoding="utf-8") as f:
    item_database = json.load(f)

@benchmark 
def adjust_to_database(name):
    lmin = len(name) * 2 + 1
    best = name

    for db_name in item_database:
        ldist = levenshtein_distance(name, db_name, costs=(2, 2, 1))
        if ldist < lmin:
            lmin = ldist
            best = db_name

        if ldist == 0:
            break
    
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
 
    return dist[row][col]


if __name__ == '__main__':    
    from PIL import Image

    for i in ["0.png", "1.png", "volt.jpg", "silver.jpg"]:
        screenshot = np.asarray(Image.open("images/" + i))
        screenshot = screenshot[:screenshot.shape[0] // 2, :]
 
        names = get_item_names(screenshot)
        print(names)
