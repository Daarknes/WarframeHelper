import os

_RES_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "res")) + os.path.sep

ITEM_DATA_LOC = _RES_LOC + "item_data.json"
MARKET_ITEM_DATA_LOC = _RES_LOC + "market_item_data.json"
MARKET_PRICE_DATA_LOC = _RES_LOC + "market_price_data.json"

CONFIG_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config")) + os.path.sep

def res_loc(app_name=None):
    if app_name:
        path = _RES_LOC + app_name + os.path.sep
    else:
        path = _RES_LOC

    # ensure the directory exists
    if not os.path.exists(path):
        os.makedirs(path)

    return path

# ensure the config/ directory exist
if not os.path.exists(CONFIG_LOC):
    os.makedirs(CONFIG_LOC)