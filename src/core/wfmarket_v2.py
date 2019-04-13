from concurrent import futures
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
import json
import os

import requests

from core import constants, itemdata
from util.printutil import ProgressBar
import time
from core.config import Config
from core.itemdata import Category
from requests.exceptions import Timeout
from util import utils
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


# _config
_config = Config()

_section_market = _config.addSection("Warframe Market")
_section_market.addEntry("BATCH_INTERVAL", 30, "How long to wait between two batches (in seconds)")
_section_market.addEntry("BATCH_SIZE", 200, "The size of each batch (the number of items/urls) when requesting market.market data")
_section_market.addEntry("MAX_CONNECTIONS", 30, "The maximum number of simultaneous threads for http-requests")
_section_market.addEntry("MAX_ORDER_AGE", 6, "Only include orders of players that are either in-game, or that have been updated in the last X hours")
_section_market.addEntry("MAX_UPDATE_AGE", 12, "The local market data (the prices) gets updated after this amount of hours")
_section_market.addEntry("RELIC_ITEMS_ONLY", True, "Only download prices for relic rewards")

_config.build()
_config.loadAndUpdate(constants.CONFIG_LOC + "warframemarket.cfg")



_loaded = False
_item_data = {}
_market_data = {}


def _update_prices():
    """
    Requires existing and valid _item_data
    """
    print("[WFMarket] updating. This may take a while.")
    order_address = "https://api.warframe.market/v1/items/{}/orders"

    market_data = _create_empty_market_data(_item_data)

    session = requests.Session()
    retry = Retry(connect=4, read=2, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
            'Accept': "application/json",
            'Content-Type': "application/json",+
            'Language': "en",
            'Platform': "pc"
        })
    
    def request_data(url):
        while True:
            try:
                response = session.get(url, timeout=(6.1, 10))
            except Timeout:
                response = None
            
            if response and response.status_code == requests.codes["ok"]:
                break
            else:
                time.sleep(2)

        return response.json()
        
    print("[WFMarket] Downloading a total of {} item-prices...".format(len(market_data)))
    first_batch = True
    for batch in utils.batch_iter(list(market_data.items()), _config['BATCH_SIZE']):
        if not first_batch:
            print("[WFMarket] sleeping {}s until next batch".format(_config['BATCH_INTERVAL']))
            time.sleep(_config['BATCH_INTERVAL'])
        first_batch = False

        
        print("[WFMarket] Starting batch (size={})".format(len(batch)))
        # "simultaneously" request the data for all items in the batch
        with ThreadPoolExecutor(max_workers=min(_config["MAX_CONNECTIONS"], len(batch))) as ex:
            future_dict = {}

            for url_name, item in batch:
                url = order_address.format(url_name)                
                future_dict[ex.submit(request_data, url)] = item
    
            progress = ProgressBar(50, len(batch))
            # parse requested data
            for future in futures.as_completed(future_dict):
                item = future_dict[future]
                wfm_item_data = future.result()
        
                try:
                    prices = _parse_price_data(wfm_item_data)
                    item.update(prices)
                except Exception as e:
                    print(item['url_name'], list(wfm_item_data.keys()))
                    raise e
        
                # update progress bar
                progress.update()
    
    session.close()

    market_data['last_update'] = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    # save the prices into a file
    with open(constants.MARKET_PRICE_DATA_LOC, "w") as f:
        json.dump(market_data, f, indent=2)
    
    global _market_data
    _market_data = market_data

    print("[WFMarket] Successfully finished updating.")


def _parse_price_data(data):
    """
    Requests prices for an item.
    """
    current_date = datetime.now()

    prices = {"buy": [], "sell": []}
    for order in data['payload']['orders']:
        # first filter on platform and visibility
        if order['visible']:
            if order['user']['status'] == "ingame":
                prices[order['order_type']].append(order['platinum'])
            # otherwise check the time since last update of the order
            else:
                last_updated = datetime.strptime(order['last_update'], "%Y-%m-%dT%H:%M:%S.%f+00:00")
                delta = current_date - last_updated
                order_age = delta.days * 24 + delta.seconds // 3600
                if order_age < _config['MAX_ORDER_AGE']:
                    prices[order['order_type']].append(order['platinum'])

    prices['buy'].sort(reverse=True)
    prices['sell'].sort()

    return prices


def _ensure_loaded():
    if not _loaded:
        raise Exception("[WFMarket] not loaded, call wfmarket.load() first.")
        

#===============================================================================
# item-data
#===============================================================================
def _parse_category(parsed_items, wfm_items, component_list=None, filter_dict=None):
    items = {}

    for item_name, item_data in parsed_items.items():
        if filter_dict and item_name not in filter_dict:
            continue

        if component_list:
            component_data = {comp_name: {} for comp_name in component_list}
        elif 'components' in item_data:
            component_data = item_data['components']
        else:
            component_data = None

        if component_data:
            if item_name + " Set" in wfm_items:
                components = {}
                for component_name, component_data in component_data.items():
                    if filter_dict and component_name not in filter_dict[item_name]:
                        continue

                    full_name = item_name + " " + component_name
                    components[component_name] = dict(component_data)
                    components[component_name]['url_name'] = wfm_items[full_name]

                # only add this entry when there are any components
                if components:
                    items[item_name] = {"url_name": wfm_items[item_name + " Set"], "components": components}

        elif item_name in wfm_items:
            items[item_name] = {"url_name": wfm_items[item_name]}
    
    return items


def _update_item_data():
    print("[WFMarket] Updating Item-data.")
    # request all warframe.market items
    response = requests.get("https://api.warframe.market/v1/items", headers={'Language': "en"})
    if response is None or response.status_code != requests.codes['ok']:
        raise Exception

    wfm_items_raw = response.json()['payload']['items']['en']
    wfm_items = {wfm_item['item_name']: wfm_item['url_name'] for wfm_item in wfm_items_raw}
    
    # stupid webpage errors
    wfm_exceptions = {
        "Decurion Barrel": "Dual Decurion Barrel",
        "Decurion Receiver": "Dual Decurion Receiver",
        "Haven": "Rift Haven"
    }
    for wfm_name, name in wfm_exceptions.items():
        wfm_items[name] = wfm_items.pop(wfm_name)


    raw_item_data = itemdata.item_data()

    filter_dict = None
    if _config['RELIC_ITEMS_ONLY']:
        filter_dict = {}

        for relic in raw_item_data[Category.RELICS].values():
            for drop in relic['drops']:
                # ignore Forma
                if drop['item'] == "Forma":
                    continue
                
                item_name = drop['item'] + " Prime"
                if item_name not in filter_dict:
                    filter_dict[item_name] = set()
    
                filter_dict[item_name].add(drop['part'])
    
    global _item_data
    _item_data = {
        Category.WEAPONS: _parse_category(raw_item_data[Category.WEAPONS], wfm_items, filter_dict=filter_dict),
        Category.WARFRAMES: _parse_category(raw_item_data[Category.WARFRAMES], wfm_items, component_list=("Blueprint", "Chassis", "Neuroptics", "Systems"), filter_dict=filter_dict),
        Category.ARCHWINGS: _parse_category(raw_item_data[Category.ARCHWINGS], wfm_items, component_list=("Wings", "Harness", "Systems"), filter_dict=filter_dict),
        Category.COMPANIONS: _parse_category(raw_item_data[Category.COMPANIONS], wfm_items, component_list=("Blueprint", "Cerebrum", "Carapace", "Systems"), filter_dict=filter_dict),
#         Category.RELICS: {}
    }

    if not _config['RELIC_ITEMS_ONLY']:
        _item_data[Category.MODS] = {mod_name: {"url_name": wfm_items[mod_name]} for mod_name in raw_item_data[Category.MODS] if mod_name in wfm_items}
        # manually add Odonata Prime Blueprint
        _item_data[Category.ARCHWINGS]['Odonata Prime']['components']['Blueprint'] = {"url_name": wfm_items['Odonata Prime Blueprint']}

    # add relics
#     for relic_name, relic_data in raw_item_data[Category.RELICS].items():
#         if relic_name + " Radiant" in wfm_items:
#             _item_data[Category.RELICS][relic_name] = relic_data
#             relic_data['url_name'] = wfm_items[relic_name + " Radiant"]


    with open(constants.MARKET_ITEM_DATA_LOC, "w") as f:
        json.dump(_item_data, f, indent=2)


def _create_empty_market_data(items):
    """
    Creates a market-data dict from the item-data in 'items' to map all 'url_name's to an empty dict, e.g.:
    {
        "ankyros_prime_blade": {},
        ...
    }
    """
    market_data = {}

    for cat_data in items.values():
        for item_data in cat_data.values():
            if "url_name" not in item_data:
                continue

            market_data[item_data['url_name']] = {}

            if "components" in item_data:
                for component_data in item_data['components'].values():
                    market_data[component_data['url_name']] = {}
    
    return market_data


#===============================================================================
# interface methods
#===============================================================================
def load(update_items=False):
    # when we want to update the item-data or the market-item-data file doesn't exist, also update prices
    if update_items or not os.path.exists(constants.MARKET_ITEM_DATA_LOC):
        # don't update item-data when only the market-item-data didn't exist or it was just updated on load
        if update_items and not itemdata.updated():
            itemdata.update()

        _update_item_data()
        _update_prices()
    else:
        global _item_data
        with open(constants.MARKET_ITEM_DATA_LOC, "r") as f:
            _item_data = json.load(f)

        # when the market-data doesn't exist yet we need to update the prices
        if not os.path.exists(constants.MARKET_PRICE_DATA_LOC):
            _update_prices()
        else:
            global _market_data
            with open(constants.MARKET_PRICE_DATA_LOC, "r") as f:
                _market_data = json.load(f)
    
            # get "last_update" time
            update_date = datetime.strptime(_market_data['last_update'], "%d-%m-%Y_%H-%M-%S")
            current_date = datetime.now()
            delta = current_date - update_date

            if (delta.days * 24 + delta.seconds / 3600) > _config["MAX_UPDATE_AGE"]:
                _update_prices()
            else:
                print("[WFMarket] Market data successfully loaded (last update was on {}).".format(datetime.strftime(update_date, "%d.%m.%Y-%H:%M:%S")))
    
    global _loaded
    _loaded = True


def update(update_items=False):
    _ensure_loaded()

    if update_items:
        itemdata.update()
        _update_item_data()
    _update_prices()

def get_update_date():
    _ensure_loaded()
    return datetime.strptime(_market_data['last_update'], "%d-%m-%Y_%H-%M-%S")


_warframe_parts = ["chassis", "systems", "neuroptics"]
_special_map = {
    "&": "and",
    "'": "",
    "-": "_"
}
def convert_to_market_name(item_name):
    words = item_name.lower().split()
    # Ember Prime Chassis Blueprint -> Ember Prime Chassis
    if [word for word in words[:-1] if word in _warframe_parts]:
        words = words[:-1]
    market_name = "_".join(words)
    
    for special_src, special_replace in _special_map.items():
        market_name = market_name.replace(special_src, special_replace)

    return market_name


def get_prices(item_name):
    _ensure_loaded()
    return _market_data[convert_to_market_name(item_name)]


def get_item_data():
    _ensure_loaded()
    return _item_data
