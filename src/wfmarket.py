import requests
import json
# from decorators import benchmark

address = 'https://api.warframe.market/v1/items/{}/orders?include=item'

keywords = ["chassis", "systems", "neuroptics"]
special_map = {
    "&": "and"
}

def convert_to_market_name(raw_item_name):
    words = raw_item_name.lower().split()
    if [word for word in words if word in keywords]:
        words = words[:-1]
    item_name = "_".join(words)
    
    for special_src, special_replace in special_map.items():
        item_name = item_name.replace(special_src, special_replace)

    return item_name

#@benchmark
def get_item_price_list(market_item_name):
    print("[WFMarket] searching on '" + address.format(market_item_name) + "' for orders.")
    page = requests.get(address.format(market_item_name))
    data = json.loads(page.content.decode("utf-8"))

    prices = []
    for order in data["payload"]["orders"]:
        if order["visible"] and order["user"]["status"] == "ingame" and order["platform"] == "pc" and order["order_type"] == "sell":
            prices.append(order["platinum"])
            
    return sorted(prices)


if __name__ == "__main__":
    get_item_price_list("rhino_prime_chassis")
    