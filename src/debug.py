import warframe_ocr
import os

from PIL import Image
import numpy as np
import wfmarket
import cProfile
from concurrent.futures.process import ProcessPoolExecutor
import pstats
from datetime import datetime
np.set_printoptions(linewidth=500)


def debug_ocr():
    def iteration(image_path):
        image = np.asarray(Image.open(image_path))
        print(warframe_ocr.get_item_names(image))
    
    folder_1080p_window = os.path.join("..", "images_1080p")
    folder_1440p_borderless = os.path.join("..", "images")
    
    for path in os.listdir(folder_1440p_borderless)[8:12]:
        iteration(os.path.join(folder_1440p_borderless, path))
        
    for path in os.listdir(folder_1080p_window)[:4]:
        iteration(os.path.join(folder_1080p_window, path))

def debug_ocr_single(image_path):
    image = np.asarray(Image.open(image_path))
    print(warframe_ocr.get_item_names(image))

def debug_full_single(image_path):
    image = np.asarray(Image.open(image_path))
    item_names = warframe_ocr.get_item_names(image)
    print(item_names)
     
    item_prices = {}
    for item_name in set(item_names):
        # exclude forma since it can't be sold
        if item_name == "FORMA BLUEPRINT" or item_name == "ERROR":
            item_prices[item_name] = ["Not sellable"]
        else:
            market_name = wfmarket.convert_to_market_name(item_name)
            item_prices[item_name] = wfmarket.get_item_prices(market_name)
     
    print(item_prices)

def debug_market(item_names):            
    item_prices = wfmarket.item_names_to_prices_map(item_names)
#     item_prices = {'EUPHONA PRIME BLUEPRINT': [2, 2, 2, 2, 2, 3, 3, 3, 5, 5, 5, 5, 5, 5], 'ZEPHYR PRIME CHASSIS BLUEPRINT': [7, 7, 7, 9, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 12, 15, 15, 20], 'KRONEN PRIME BLUEPRINT': [2, 2, 3, 3, 4, 4, 5, 7, 8, 9, 9, 10, 10]}
#     print(item_prices)
#     for name, prices in item_prices.items():
#         if prices is not None and prices != 0:
#             print(sum(prices) / len(prices))


if __name__ == "__main__":
#     debug_ocr_single(os.path.join("..", "images", "03-11-2018_12-46-22.png"))
#     debug_ocr_single(os.path.join("..", "images_1080p", "03-11-2018_15-35-35.png"))
    
#     date = datetime.strptime('2018-04-17T18:05:12.000+00:00', "%Y-%m-%dT%H:%M:%S.%f+00:00")
#     print(date)
    
#     prof = cProfile.Profile()
#     prof.enable()
    debug_market(['EUPHONA PRIME BLUEPRINT', 'KRONEN PRIME BLUEPRINT', 'ZEPHYR PRIME CHASSIS BLUEPRINT', 'EUPHONA PRIME BLUEPRINT'])
#     prof.disable()
#     
#     prof.dump_stats("perftest.cprof")
#     stats = pstats.Stats("perftest.cprof")
#     stats.sort_stats("time").print_stats(40)
        
#     prof.print_stats(sort="time")
    