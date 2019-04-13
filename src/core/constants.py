import os

RES_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "res")) + os.path.sep

ITEM_DATA_LOC = RES_LOC + "item_data.json"
MARKET_ITEM_DATA_LOC = RES_LOC + "market_item_data.json"
MARKET_PRICE_DATA_LOC = RES_LOC + "market_price_data.json"

CONFIG_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config")) + os.path.sep


# ensure the res/ and config/ directories exist
if not os.path.exists(RES_LOC):
    os.makedirs(RES_LOC)

if not os.path.exists(CONFIG_LOC):
    os.makedirs(CONFIG_LOC)