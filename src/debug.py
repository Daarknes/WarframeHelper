import warframe_ocr
import os

from PIL import Image
import numpy as np
import wfmarket
np.set_printoptions(linewidth=500)



def debug_ocr(image_path):
    def iteration(image_path):
        image = np.asarray(Image.open(image_path))
        print(warframe_ocr.get_item_names(image))
    
    folder_1080p_window = os.path.join("..", "images_1080p")
    folder_1440p_borderless = os.path.join("..", "images")
    
    for path in os.listdir(folder_1440p_borderless)[8:12]:
        iteration(os.path.join(folder_1440p_borderless, path))
        
    for path in os.listdir(folder_1080p_window)[:4]:
        iteration(os.path.join(folder_1080p_window, path))


image = np.asarray(Image.open(os.path.join("..", "images", "03-11-2018_23-12-49.png")))
item_names = warframe_ocr.get_item_names(image)
print(item_names)
 
item_prices = {}
for item_name in set(item_names):
    # exclude forma since it can't be sold
    if item_name == "FORMA BLUEPRINT" or item_name == "ERROR":
        item_prices[item_name] = ["Not sellable"]
    else:
        market_name = wfmarket.convert_to_market_name(item_name)
        item_prices[item_name] = wfmarket.get_item_price_list(market_name)
 
print(item_prices)