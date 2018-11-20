import requests
import json
from datetime import datetime
import traceback
import sys
import os
from core import constants


_address = "https://api.warframe.market/v1/items/{}/orders?include=item"

_warframe_parts = ["chassis", "systems", "neuroptics"]
_special_map = {
    "&": "and"
}

def _convert_to_market_name(raw_item_name):
    words = raw_item_name.lower().split()
    if [word for word in words if word in _warframe_parts]:
        words = words[:-1]
    market_name = "_".join(words)
    
    for special_src, special_replace in _special_map.items():
        market_name = market_name.replace(special_src, special_replace)

    return market_name

#@benchmark
def _request_prices(market_item_name, max_order_age):
    try:
        print("[WFMarket] searching on '" + _address.format(market_item_name) + "' for orders.")
        page = requests.get(_address.format(market_item_name))
        data = json.loads(page.content.decode("utf-8"))
        current_date = datetime.now()
    
        prices = []
        for order in data["payload"]["orders"]:
            # first filter on platform, order type (we only want sell values) and visibility
            if order["platform"] == "pc" and order["order_type"] == "sell" and order["visible"]:
                if order["user"]["status"] == "ingame":
                    prices.append(order["platinum"])
                # otherwise check the time since last update of the order
                else:
                    last_updated = datetime.strptime(order["last_update"], "%Y-%m-%dT%H:%M:%S.%f+00:00")
                    delta = current_date - last_updated
                    order_age = delta.days * 24 + delta.seconds // 3600
                    if order_age < max_order_age:
                        prices.append(order["platinum"])
                
        return sorted(prices)
    except:
        print("[WFMarket] Error while requesting data for '{}'".format(market_item_name), traceback.print_exc(file=sys.stdout))
        return None

def load(max_update_age, max_order_age):
    global _market_data, _names_to_prices

    if not os.path.exists(constants.MARKET_PRICES):
        update(max_order_age)
    else:
        with open(constants.MARKET_PRICES, "r") as f:
            _market_data = json.load(f)
        
        current_date = datetime.now()
        update_date = datetime.strptime(_market_data["last_update"], "%d-%m-%Y_%H-%M-%S")
        delta = current_date - update_date
        if (delta.days * 24 + delta.seconds // 3600) > max_update_age:
            update(max_order_age)
        else:
            for item_name, item_data in _market_data["items"].items():
                for component_name, prices in item_data["components"].items():
                    if prices is not None:
                        _names_to_prices[item_name + "_" + component_name] = prices
            print("[WFMarket] Market data successfully loaded (last update was on {}).".format(datetime.strftime(update_date, "%d.%m.%Y-%H:%M:%S")))
    
    global _loaded
    _loaded = True

def _process_item(market_item_names, item_name, components, max_order_age):
    global _market_data, _names_to_prices

    # first request the set prices
    set_prices = _request_prices(item_name + "_set", max_order_age)
    
    component_data = {}
    _market_data["items"][item_name] = {"set": set_prices, "components": component_data}
    
    for component_name in components:
        # this component is a separate item (not a part)
        if component_name in market_item_names:
            # mark as reference via None
            component_data[component_name] = None
            _process_item(market_item_names, component_name, market_item_names[component_name], max_order_age)
        else:
            prices = _request_prices(item_name + "_" + component_name, max_order_age)
            component_data[component_name] = prices
            _names_to_prices[item_name + "_" + component_name] = prices

def update(max_order_age):
    global _market_data, _names_to_prices
    
    print("[WFMarket] updating market prices. This may take a while.")
    with open(constants.MARKET_ITEM_DATA, "r", encoding="utf-8") as f:
        market_item_names = json.load(f)

    _market_data.clear()
    _names_to_prices.clear()
    
    _market_data["last_update"] = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    _market_data["items"] = {}
    
    for item_name, components in market_item_names.items():
        if item_name not in _market_data["items"]:
            _process_item(market_item_names, item_name, components, max_order_age)
    
    with open(constants.MARKET_PRICES, "w") as f:
        json.dump(_market_data, f, indent="  ")

def item_names_to_prices_map(item_names):
    if not _loaded:
        raise Exception("[WFMarket] not loaded, call wfmarket.load(max_update_age, max_order_age) first.")

    name_to_prices = {}
    
    for item_name in set(item_names):
        # exclude forma since it can't be sold
        if item_name == "FORMA BLUEPRINT" or item_name == "ERROR":
            name_to_prices[item_name] = []
        else:
            market_name = _convert_to_market_name(item_name)
            name_to_prices[item_name] = _names_to_prices[market_name]

    return name_to_prices

def get_all():
    if not _loaded:
        raise Exception("[WFMarket] not loaded, call wfmarket.load(max_update_age, max_order_age) first.")

    return _market_data["items"]

_loaded = False
_market_data = {}
_names_to_prices = {}
