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

CAT_ITEMS = "items"
CAT_MODS = "mods"

# _config
_config = Config()

_section_market = _config.addSection("Warframe Market")
_section_market.addEntry("MAX_CONNECTIONS", 100, "The maximum number of simultaneous threads for http-requests")
_section_market.addEntry("MAX_ORDER_AGE", 8, "only include orders of players that are either in-game, or that have been updated in the last X hours")
_section_market.addEntry("MAX_UPDATE_AGE", 24, "The local market data (the prices) gets updated after this amount of hours")

_config.build()
_config.loadAndUpdate(os.path.join(constants.CONFIG_LOC, "warframemarket.cfg"))

def _convert_to_market_name(raw_item_name):
    words = raw_item_name.lower().split()
    if [word for word in words if word in _warframe_parts]:
        words = words[:-1]
    market_name = "_".join(words)
    
    for special_src, special_replace in _special_map.items():
        market_name = market_name.replace(special_src, special_replace)

    return market_name

class _Info():
    def __init__(self, name, category, bonus=None):
        self.name = name
        self.category = category
        self.bonus = bonus
    
    def __str__(self):
        return self.name + ("" if self.bonus is None else "_" + self.bonus)

    def __repr__(self):
        return "[{}] {}".format(self.category, self.name) + ("" if self.bonus is None else "_" + self.bonus)

def load():
    global _name_to_info, _market_prices

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
            for item_name, item_data in _market_prices["items"].items():
                info = _Info(item_name, CAT_ITEMS, "set")
                _name_to_info[str(info)] = info
                for component_name in item_data["components"].keys():
                    info = _Info(item_name, CAT_ITEMS, component_name)
                    _name_to_info[str(info)] = info
            
            for mod_name in _market_prices["mods"].keys():
                info = _Info(mod_name, CAT_MODS)
                _name_to_info[str(info)] = info

            print("[WFMarket] Market data successfully loaded (last update was on {}).".format(datetime.strftime(update_date, "%d.%m.%Y-%H:%M:%S")))
    
    global _loaded
    _loaded = True

def update():
    global _name_to_info, _market_prices
    
    print("[WFMarket] updating market prices. This may take a while.")
    with open(constants.MARKET_NAMES_LOC, "r", encoding="utf-8") as f:
        market_names = json.load(f)

    _market_prices = {
        "last_update": datetime.now().strftime("%d-%m-%Y_%H-%M-%S"),
        "items": {},
        "mods": {}
    }
    
    infos =  []

    for item_name, components in market_names["items"].items():
        info = _Info(item_name, CAT_ITEMS, "set")
        _name_to_info[str(info)] = info
        infos.append(info)

        for comp_name in set(components):
            # only add components, not separate items (this is not a part)
            if comp_name not in market_names["items"]:
                info = _Info(item_name, CAT_ITEMS, comp_name)
                _name_to_info[str(info)] = info
                infos.append(info)

    for mod_name in market_names["mods"]:
        info = _Info(mod_name, CAT_MODS)
        _name_to_info[str(info)] = info
        infos.append(info)
    
    i = 0
    progress = ProgressBar(40, len(infos))
    def request_prices(info):
        prices = _request_prices(str(info))
        # update progress bar
        nonlocal i
        i += 1
        progress.update(i)
        return prices
    
    with ThreadPoolExecutor(max_workers=_config["MAX_CONNECTIONS"]) as ex:
        prices = ex.map(request_prices, infos)

    for info, prices in zip(infos, prices):
        if info.category == CAT_ITEMS:
            # when the item is not yet present, add an entry in the dict
            if info.name not in _market_prices["items"]:
                _market_prices["items"][info.name] = {}
            
            item_data = _market_prices["items"][info.name]
            if info.bonus == "set":
                item_data["set"] = prices
            else:
                if "components" not in item_data:
                    item_data["components"] = {}
                item_data["components"][info.bonus] = prices
        elif info.category == CAT_MODS:
            _market_prices["mods"][info.name] = prices
    
    with open(constants.MARKET_PRICES_LOC, "w") as f:
        json.dump(_market_prices, f, indent=2)

def _request_prices(market_item_name):
    response = None
    try:
#         print("[WFMarket] searching on '" + _address.format(market_item_name) + "' for orders.")
        while True:
            response = requests.get(_address.format(market_item_name))
            if response.status_code == requests.codes["not_found"]:
                return None
            elif response.status_code == requests.codes["ok"]:
                break
#             elif response.status_code == requests.codes["service_unavailable"]:
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

def item_names_to_prices_map(ocr_item_names):
    if not _loaded:
        raise Exception("[WFMarket] not loaded, call wfmarket.load(max_update_age, max_order_age) first.")

    name_to_prices = {}
    
    for item_name in set(ocr_item_names):
        # exclude forma since it can't be sold
        if item_name == "FORMA BLUEPRINT" or item_name == "ERROR":
            name_to_prices[item_name] = []
        else:
            market_name = _convert_to_market_name(item_name)
            info = _name_to_info[market_name]
            if info.category == CAT_ITEMS:
                if info.bonus == "set":
                    name_to_prices[item_name] = _market_prices["items"][info.name]["set"]["sell"]
                else:                
                    name_to_prices[item_name] = _market_prices["items"][info.name]["components"][info.bonus]["sell"]
            elif info.category == CAT_MODS:
                name_to_prices[item_name] = _market_prices["mods"][info.name]

    return name_to_prices

def get_all(category):
    if not _loaded:
        raise Exception("[WFMarket] not loaded, call wfmarket.load(max_update_age, max_order_age) first.")

    return _market_prices[category]

_loaded = False
_name_to_info = {}
_market_prices = {}
