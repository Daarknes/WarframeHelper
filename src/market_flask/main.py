from core.config import Config, FunctionBlock
from core import constants
from flask import Flask, render_template
from market_flask import instance
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from util import logger
from util.utils import NoneFloat
logger.init("out.log")


config = Config()

section_funcs = config.addSection("Functions")
section_funcs.addEntry("calc_buy_repr", FunctionBlock(r'''if not prices["buy"]:
    sell_repr = calc_sell_repr(prices)
    return sell_repr * 3 // 4 if sell_repr else None
else:
    # for buying only include the most expensive 10%
    n = int(len(prices["buy"]) * 0.1 + 0.95)
    return sum(prices["buy"][:n]) // n''', "prices"), "calculates a buy-price-representative from price-data for a single component")

section_funcs.addEntry("calc_sell_repr", FunctionBlock(r'''if not prices["sell"]:
    return None
else:
    # take 0.1 quantile for selling representative
    n = int(0.1 * len(prices["sell"]))
    return prices["sell"][n]''', "prices"), "calculates a sell-price-representative from price-data for a single component")

section_funcs.addEntry("calc_component_repr", FunctionBlock(r'''comp_repr = 0
for comp_prices in prices:
    if comp_prices is None:
        return None
    
    if order_type == "buy":
        price_repr = calc_buy_repr(comp_prices)
    else:
        price_repr = calc_sell_repr(comp_prices)

    if price_repr is None:
        return None

    comp_repr += price_repr
return comp_repr''', "prices, order_type"), "calculates a buy-price-representative for a set of components from price-data")

config.build()
config.loadAndUpdate(constants.CONFIG_LOC + "markethelper.cfg")
instance.setConfig(config)


# times at which the data gets updated
time_points = [
    {'hour': 7, 'minute': 53},
    {'hour': 10, 'minute': 53},
    {'hour': 14, 'minute': 53},
    {'hour': 18, 'minute': 53},
    {'hour': 21, 'minute': 53}
]
    

def create_tables(table_sets_old=None, table_single_old=None):
    item_data = wfmarket_v2.get_item_data()
    
    table_sets = {}
    table_single = {}
    list_sets = []
    list_single = []

    for cat_data in item_data.values():
        for item_name, item_data in cat_data.items():
            item_prices = wfmarket_v2.get_prices(item_data['url_name'])
            item_sell_repr = instance.config["calc_sell_repr"](item_prices)
            item_buy_repr = instance.config["calc_buy_repr"](item_prices)

            # this item consist of a set
            if 'components' in item_data:
                # TODO: change this calculation
                component_prices = []
                components = []
                for comp_name, comp_data in item_data['components'].items():
                    comp_prices = wfmarket_v2.get_prices(comp_data['url_name'])

                    count = comp_data['count'] if 'count' in comp_data else 1
                    component_prices.extend([comp_prices] * count)
                    components.extend([comp_name] * count)
                
                comp_buy_repr = instance.config["calc_component_repr"](component_prices, "buy")

                # buy the components and sell the set
                profit = NoneFloat(item_sell_repr) - comp_buy_repr
                summary_components = {
                    'sell': item_sell_repr,
                    'buy': comp_buy_repr,
                    'profit': profit.value,
                    'profit_trade': (profit / (len(components) + 1)).value
                }
                
                list_entry = {
                    'name': item_name,
                    'buy_type': 'Components',
                    'components': ", ".join(map(str, components))
                }
                list_entry.update(summary_components)
                list_entry.update(get_deltas(summary_components, table_sets_old[item_name]['Components'] if table_sets_old else summary_components))
                list_sets.append(list_entry)

                # buy the set and sell the set
                profit = NoneFloat(item_sell_repr) - item_buy_repr
                summary_set = {
                    'sell': item_sell_repr,
                    'buy': item_buy_repr,
                    'profit': profit.value,
                    'profit_trade': (profit / 2).value
                }
                
                list_entry = {
                    'name': item_name,
                    'buy_type': 'Set',
                    'components': ", ".join(map(str, components))
                }
                list_entry.update(summary_set)
                list_entry.update(get_deltas(summary_set, table_sets_old[item_name]['Set'] if table_sets_old else summary_set))
                list_sets.append(list_entry)

                # add summaries to the tables (for later)
                table_sets[item_name] = {
                    'Components': summary_components,
                    'Set': summary_set
                }
            else:
                summary = {
                    'sell': item_sell_repr,
                    'buy': item_buy_repr,
                    'profit': (NoneFloat(item_sell_repr) - item_buy_repr).value
                }

                list_entry = { 'name': item_name }
                list_entry.update(summary)
                list_entry.update(get_deltas(summary, table_single_old[item_name] if table_single_old else summary))
                list_single.append(list_entry)
                
                table_single[item_name] = summary
    
    # initial sorting
    list_sets.sort(key=lambda entry: -1e3 if entry['profit'] is None else entry['profit'], reverse=True)
    list_single.sort(key=lambda entry: -1e3 if entry['profit'] is None else entry['profit'], reverse=True)

    return table_sets, table_single, list_sets, list_single


def get_deltas(data, old_data):
    deltas = {}
    for key, val in data.items():
        deltas[key+'_delta'] = (NoneFloat(val) - old_data[key]).value
    return deltas



app = Flask(__name__)

@app.route("/")
def index():
    timespamp = datetime.strftime(wfmarket_v2.get_update_date(), "%H:%M")
    return render_template("markethelper.html", last_update=timespamp, list_sets=_list_sets, list_single=_list_single)

def update():
    wfmarket_v2.update()
    global _table_sets, _table_single, _list_sets, _list_single
    _table_sets, _table_single, _list_sets, _list_single = create_tables(_table_sets, _table_single)


if __name__ == "__main__":
    from core import wfmarket_v2
    wfmarket_v2.load()
    
    scheduler = BackgroundScheduler()
    for time_point in time_points:
        scheduler.add_job(update, 'cron', **time_point)
 
    scheduler.start()
    _table_sets, _table_single, _list_sets, _list_single = create_tables()
    app.run(host="::", port=80, debug=False)

    scheduler.shutdown()
