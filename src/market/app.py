from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QTableWidget, QTableWidgetItem

from core import constants, wfmarket
from PyQt5.Qt import Qt
import json


def calc_sell_repr(prices):
    # take 0.3 quantile for selling representant
    return prices[int(0.3 * len(prices))]

def calc_buy_repr(prices):
    # for buying only include the cheapest 4
    return sum(prices[:10]) // len(prices[:10])

def calc_profit(set_price, component_price):
    return set_price - component_price

def calc_comp_repr(component_prices, components):
    comp_repr = 0

    for comp_name in components:
        comp_prices = component_prices[comp_name]
        print(comp_name, comp_prices)
        if comp_prices is None:
            return None
        comp_repr += calc_buy_repr(comp_prices)
    
    return comp_repr
    

class Window(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        
        self.setWindowTitle("Warframe Market Helper")
        self.setWindowIcon(QIcon(constants.PATH_RES + "relic.png"))
        self.resize(QSize(1200, 700))
        self.setupUi()
    
    def setupUi(self):
        market_data = wfmarket.get_all()

        table = QTableWidget(self)
        table.setColumnCount(4)
        table.setRowCount(len(market_data))
        table.setHorizontalHeaderLabels(["Name", "Set", "Components", "profit"])
        table.verticalHeader().hide()
        
        with open(constants.MARKET_ITEM_DATA, "r", encoding="utf-8") as f:
            market_item_names = json.load(f)

        debug = {"akstiletto_prime": [
    "barrel",
    "barrel",
    "blueprint",
    "link",
    "receiver",
    "receiver"
  ]}
        for i, (item_name, components) in enumerate(debug.items()): #enumerate(market_item_names.items()):
            item_prices = market_data[item_name]
            set_repr = calc_sell_repr(item_prices["set"])
            
            comp_repr = calc_comp_repr(item_prices["components"], components)
            if comp_repr is None:
                continue

            
            table.setItem(i, 0, QTableWidgetItem(" ".join(item_name.split("_"))))

            item = QTableWidgetItem()
            item.setData(Qt.EditRole, set_repr)
            table.setItem(i, 1, item)

            item = QTableWidgetItem()
            item.setData(Qt.EditRole, comp_repr)
            table.setItem(i, 2, item)

            item = QTableWidgetItem()
            item.setData(Qt.EditRole, calc_profit(set_repr, comp_repr))
            table.setItem(i, 3, item)

        table.sortByColumn(3, Qt.DescendingOrder)
        table.setSortingEnabled(True)

        self.setCentralWidget(table)
