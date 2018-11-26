import os

RES_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "res")) + os.path.sep
MARKET_NAMES_LOC = os.path.join(RES_LOC, "market_names.json")
OCR_NAMES_LOC = os.path.join(RES_LOC, "ocr_names.json")
MARKET_PRICES_LOC = os.path.join(RES_LOC, "market_prices.json")

CONFIG_LOC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config")) + os.path.sep


# ensure the res/ and config/ directories exist
if not os.path.exists(RES_LOC):
    os.makedirs(RES_LOC)

if not os.path.exists(CONFIG_LOC):
    os.makedirs(CONFIG_LOC)