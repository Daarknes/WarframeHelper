import requests
import json
from datetime import datetime
import traceback
import sys
import os
from core import constants
from concurrent.futures.thread import ThreadPoolExecutor
from util.printutil import ProgressBar
import time
from core.config import Config


_address = "https://api.warframe.market/v1/items/{}/orders?include=item"

_warframe_parts = ["chassis", "systems", "neuroptics"]
_special_map = {
    "&": "and",
    "'": "",
    "-": "_"
}

# _config
_config = Config()

_section_market = _config.addSection("Warframe Market")
_section_market.addEntry("MAX_CONNECTIONS", 100, "The maximum number of simultaneous threads for http-requests")
_section_market.addEntry("MAX_ORDER_AGE", 8, "only include orders of players that are either in-game, or that have been updated in the last X hours")
_section_market.addEntry("MAX_UPDATE_AGE", 24, "The local market data (the prices) gets updated after this amount of hours")

_config.build()
_config.loadAndUpdate(os.path.join(constants.CONFIG_LOC, "warframemarket.cfg"))


def _convert_to_market_name(ocr_item_name):
    words = ocr_item_name.lower().split()
    if [word for word in words[:-1] if word in _warframe_parts]:
        words = words[:-1]
    market_name = "_".join(words)
    
    for special_src, special_replace in _special_map.items():
        market_name = market_name.replace(special_src, special_replace)

    return market_name

CAT_ITEMS = "items"
CAT_MODS = "mods"
CAT_RELICS = "relics"

class _Info():
    def __init__(self, name, categoty):
        self.name = name
        self.category = categoty
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return "[{}] {}".format(self.category, self.name)

def load():
    global _market_prices

    if not os.path.exists(constants.MARKET_PRICES_LOC):
        update()
    else:
        with open(constants.MARKET_PRICES_LOC, "r") as f:
            _market_prices = json.load(f)
        
        current_date = datetime.now()
        update_date = datetime.strptime(_market_prices["last_update"], "%d-%m-%Y_%H-%M-%S")
        delta = current_date - update_date
        if (delta.days * 24 + delta.seconds // 3600) > _config["MAX_UPDATE_AGE"]:
            update()
        else:
            print("[WFMarket] Market data successfully loaded (last update was on {}).".format(datetime.strftime(update_date, "%d.%m.%Y-%H:%M:%S")))
    
    global _loaded
    _loaded = True

def update():
    global _market_prices
    
    print("[WFMarket] updating market prices. This may take a while.")
    with open(constants.MARKET_NAMES_LOC, "r", encoding="utf-8") as f:
        market_names = json.load(f)

# debug
#     market_names = {
#         "items": {
#             "akbolto_prime": [
#                 "barrel",
#                 "barrel",
#                 "blueprint",
#                 "link",
#                 "receiver",
#                 "receiver"]
#         },
#         "mods": [
#             "abating_link"
#         ],
#         "relics": {
#             "lith_c2_intact": [
#                 [
#                     "akbolto_prime_barrel",
#                     0.11
#                 ]
#             ]
#         }
#     }

    _market_prices = {
        "last_update": datetime.now().strftime("%d-%m-%Y_%H-%M-%S"),
        CAT_ITEMS: {},
        CAT_MODS: {},
        CAT_RELICS: {}
    }
    
    # accumulate all market names to request them "simultaneously" (via Threading)
    infos =  []
    for item_name, components in market_names[CAT_ITEMS].items():
        infos.append(_Info(item_name + "_set", CAT_ITEMS))

        for comp_name in set(components):
            # only add components, not separate items (this is not a part)
            if comp_name not in market_names[CAT_ITEMS]:
                infos.append(_Info(item_name + "_" + comp_name, CAT_ITEMS))

    for mod_name in market_names[CAT_MODS]:
        infos.append(_Info(mod_name, CAT_MODS))
    
    for relic_name, relic_types in market_names[CAT_RELICS].items():
        for relic_type in relic_types.keys():
            infos.append(_Info(relic_name + "_" + relic_type, CAT_RELICS))
    
    # helper method for requesting prices and updating the loading bar
    i = 0
    progress = ProgressBar(40, len(infos))
    def request_prices(info):
        prices = _request_prices(str(info))
        # update progress bar
        nonlocal i
        i += 1
        progress.update(i)
        return prices
    
    # "simultaneously" request the prices for all market names
    with ThreadPoolExecutor(max_workers=_config["MAX_CONNECTIONS"]) as ex:
        prices = ex.map(request_prices, infos)
    # and put them into the data structure
    for info, prices in zip(infos, prices):
        _market_prices[info.category][info.name] = prices
    
    # save the prices into a file
    with open(constants.MARKET_PRICES_LOC, "w") as f:
        json.dump(_market_prices, f, indent=2)

def _request_prices(market_item_name):
    response = None
    try:
#         print("[WFMarket] searching on '" + _address.format(market_item_name) + "' for orders.")
        while True:
            response = requests.get(_address.format(market_item_name))

            if response is None:
                print(market_item_name + " needs retry")
                # try again in 1s
                time.sleep(1.0)
                continue
            elif response.status_code == requests.codes["not_found"]:
                return None
            elif response.status_code == requests.codes["ok"]:
                break
            else:
                print(market_item_name + " needs retry")
                # try again in 1s
                time.sleep(1.0)
                continue

        data = json.loads(response.content.decode("utf-8"))
        current_date = datetime.now()
    
        prices = {"buy": [], "sell": []}
        for order in data["payload"]["orders"]:
            # first filter on platform, order type (we only want sell values) and visibility
            if order["platform"] == "pc" and order["visible"]:
                if order["user"]["status"] == "ingame":
                    prices[order["order_type"]].append(order["platinum"])
                # otherwise check the time since last update of the order
                else:
                    last_updated = datetime.strptime(order["last_update"], "%Y-%m-%dT%H:%M:%S.%f+00:00")
                    delta = current_date - last_updated
                    order_age = delta.days * 24 + delta.seconds // 3600
                    if order_age < _config["MAX_ORDER_AGE"]:
                        prices[order["order_type"]].append(order["platinum"])

        prices["buy"].sort(reverse=True)
        prices["sell"].sort()
        return prices
    except:
        print("[WFMarket] Error while requesting data for '{}' (status code {})".format(market_item_name, response.status_code if response else response))
        print(traceback.print_exc(file=sys.stdout))
        return None

def _ensure_loaded():
    if not _loaded:
        raise Exception("[WFMarket] not loaded, call wfmarket.load() first.")

def item_names_to_prices_map(ocr_item_names):
    _ensure_loaded()
    name_to_prices = {}
    
    for item_name in set(ocr_item_names):
        # exclude forma since it can't be sold
        if item_name == "FORMA BLUEPRINT" or item_name == "ERROR":
            name_to_prices[item_name] = []
        else:
            market_name = _convert_to_market_name(item_name)
            name_to_prices[item_name] = _market_prices["items"][market_name]["sell"]

    return name_to_prices

def get_all(category):
    _ensure_loaded()
    return _market_prices[category]

_loaded = False
_market_prices = {}
