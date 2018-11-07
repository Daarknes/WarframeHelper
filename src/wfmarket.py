import requests
import json
from datetime import datetime
import config
import traceback
import sys
# from decorators import benchmark

address = 'https://api.warframe.market/v1/items/{}/orders?include=item'

warframe_parts = ["chassis", "systems", "neuroptics"]
special_map = {
    "&": "and"
}

def _convert_to_market_name(raw_item_name):
    words = raw_item_name.lower().split()
    if [word for word in words if word in warframe_parts]:
        words = words[:-1]
    market_name = "_".join(words)
    
    for special_src, special_replace in special_map.items():
        market_name = market_name.replace(special_src, special_replace)

    return market_name

#@benchmark
def _get_item_prices(market_item_name):
    try:
        print("[WFMarket] searching on '" + address.format(market_item_name) + "' for orders.")
        page = requests.get(address.format(market_item_name))
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
                    if order_age < config.config["MAX_ORDER_AGE"]:
                        prices.append(order["platinum"])
                
        return sorted(prices)
    except:
        print("[WFMarket] Error while requesting data for '{}'".format(market_item_name), traceback.print_exc(file=sys.stdout))
        return None

def item_names_to_prices_map(item_names):
    name_to_prices = {}
    
    for item_name in set(item_names):
        # exclude forma since it can't be sold
        if item_name == "FORMA BLUEPRINT" or item_name == "ERROR":
            name_to_prices[item_name] = []
        else:
            market_name = _convert_to_market_name(item_name)
            name_to_prices[item_name] = _get_item_prices(market_name)

    return name_to_prices


if __name__ == "__main__":
    _get_item_prices("rhino_prime_chassis")
    