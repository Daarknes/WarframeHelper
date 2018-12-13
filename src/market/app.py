import json

from PyQt5.Qt import Qt
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QTableWidget, QTableWidgetItem, QTabWidget, QHeaderView

from core import constants, wfmarket
from market import instance
from collections import defaultdict
import code


def calc_profit(sell_price, buy_price):
    if not sell_price or not buy_price:
        return None
    else:
        return sell_price - buy_price


class Window(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        
        self.setWindowTitle("Warframe Market Helper")
        self.setWindowIcon(QIcon(constants.RES_LOC + "relic.png"))
        self.resize(QSize(1200, 700))
        self.setupUi()
    
    def setupUi(self):
        wTabs = QTabWidget()
        self.setCentralWidget(wTabs)
        
        with open(constants.MARKET_NAMES_LOC, "r", encoding="utf-8") as f:
            market_names = json.load(f)

        wTabs.addTab(self.createItemTable(market_names), "Parts")
        wTabs.addTab(self.createModTable(market_names), "Mods")
        
        wTabs.addTab(self.createRelicTable(market_names), "Relics")

    def createItemTable(self, market_names):
        market_data = wfmarket.get_all(wfmarket.CAT_ITEMS)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setRowCount(len(market_data))
        table.setHorizontalHeaderLabels(["Name", "Set (Sell)", "Components (Sell)", "Components (Buy)", "Potential Profit"])
        table.verticalHeader().hide()

        for i, (item_name, components) in enumerate(market_names["items"].items()):
            set_repr = instance.config["calc_sell_repr"](market_data[item_name + "_set"])
            
            component_prices = [market_data[item_name + "_" + comp_name] for comp_name in components]
            
            comp_sell_repr = instance.config["calc_component_repr"](component_prices, "sell")
            comp_buy_repr = instance.config["calc_component_repr"](component_prices, "buy")

            
            table.setItem(i, 0, QTableWidgetItem(" ".join(item_name.split("_"))))

            item = QTableWidgetItem()
            item.setData(Qt.EditRole, set_repr)
            table.setItem(i, 1, item)

            item = QTableWidgetItem()
            item.setData(Qt.EditRole, comp_sell_repr)
            table.setItem(i, 2, item)

            item = QTableWidgetItem()
            item.setData(Qt.EditRole, comp_buy_repr)
            table.setItem(i, 3, item)

            item = QTableWidgetItem()
            item.setData(Qt.EditRole, calc_profit(set_repr, comp_buy_repr))
            table.setItem(i, 4, item)

        table.sortByColumn(4, Qt.DescendingOrder)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table
    
    def createModTable(self, market_names):
        market_data = wfmarket.get_all(wfmarket.CAT_MODS)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setRowCount(len(market_data))
        table.setHorizontalHeaderLabels(["Name", "Sell Price", "Buy Price", "Potential Profit"])
        table.verticalHeader().hide()

        for i, mod_name in enumerate(market_names["mods"]):
            mod_prices = market_data[mod_name]
            if mod_prices is None:
                continue
            
            buy_repr = instance.config["calc_buy_repr"](mod_prices)
            sell_repr = instance.config["calc_sell_repr"](mod_prices)

            table.setItem(i, 0, QTableWidgetItem(" ".join(mod_name.split("_"))))

            item = QTableWidgetItem()
            item.setData(Qt.EditRole, sell_repr)
#                 item.setData(Qt.DisplayRole, "-")
            table.setItem(i, 1, item)

            item = QTableWidgetItem()
            item.setData(Qt.EditRole, buy_repr)
            table.setItem(i, 2, item)
            
            item = QTableWidgetItem()
            item.setData(Qt.EditRole, calc_profit(sell_repr, buy_repr))
            table.setItem(i, 3, item)

        table.sortByColumn(3, Qt.DescendingOrder)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    
    def createRelicTable(self, market_names):
        
        cutoff_price = 7
        
        
        relic_data = wfmarket.get_all(wfmarket.CAT_RELICS)
        item_data = wfmarket.get_all(wfmarket.CAT_ITEMS)
        
        relic_list = []
        
        #0: intact income
        #1: intact price
        #2: radiant income
        #3: radiant price
        relics = defaultdict(list)
        
        code.interact(local=locals())
        
        for i, (relic_name, components) in enumerate(market_names["relics"].items()):
            
            relic_price = relic_data[relic_name]
            
            truncated_name = relic_name[:relic_name.rfind("_")]
            
            if relic_price is None: #if we have no data for this relic, we don't want to show it
                continue
            
            buy_repr = instance.config["calc_buy_repr"](relic_price)            
            sell_repr = instance.config["calc_sell_repr"](relic_price)
            
            invalid_flag = True
            
            if (buy_repr == None):
                buy_repr = 9999999
            else:
                invalid_flag = False
            
            if (sell_repr == None):
                sell_repr = 9999999
            else:
                invalid_flag = False
                
            #best_relic_price = min(buy_repr, sell_repr)
            best_relic_price = sell_repr #a lot of people try to buy relics way too cheap
            
            
            if (best_relic_price == 0 or invalid_flag):
                continue #We can't buy this relic, so we can skip it
            
            if not (truncated_name in relics): #fill it with zero values in case a relic is not availabe in one rarity
                relics[truncated_name].append(0)
                relics[truncated_name].append(0)
                relics[truncated_name].append(0)
                relics[truncated_name].append(0)
            
            income = 0
            
            #calculate the expected income for the current relic
            for (component_name, component_probability) in components:
                current_component = item_data[component_name]
            
                if current_component is None:
                    continue
            
                buy_repr = instance.config["calc_buy_repr"](current_component)
                sell_repr = instance.config["calc_sell_repr"](current_component)
                
                best_item_price = max(buy_repr, sell_repr)
                
                if (best_item_price < cutoff_price):
                    best_item_price = 0
                
                income = income + (best_item_price * component_probability)
            
            if ("intact" in relic_name):
                relics[truncated_name][0] = income
                relics[truncated_name][1] = best_relic_price
            else:
                relics[truncated_name][2] = income
                relics[truncated_name][3] = best_relic_price  
        
        
        table = QTableWidget()
        table.setColumnCount(7)
        table.setRowCount(len(relics))
        table.setHorizontalHeaderLabels(["Name", "Price Intact", "Potential Profit Intact", "Profit per person (int)", "Price Radiant", "Potential Profit Radiant", "Profit per person (rad)"])
        table.verticalHeader().hide()

        #code.interact(local=locals())   
        for i, (relic_name, (int_income, int_price, rad_income, rad_price)) in enumerate(relics.items()):
            
            item = QTableWidgetItem(" ".join(relic_name.split("_")))
            
            #item = item.setToolTip('This is a tooltip message.')
            
            
            table.setItem(i, 0, item)
            
            cleaned_int_price = int_price
            if (int_price <= 0 or int_price > 100000):
                cleaned_int_price = "-"
            item = QTableWidgetItem()
            item.setData(Qt.EditRole, cleaned_int_price)
            table.setItem(i, 1, item)
            
            item = QTableWidgetItem()
            item.setData(Qt.EditRole, int_income)
            table.setItem(i, 2, item)
            
            price_value = ((rad_income * 4) - int_price) / 4
            if (price_value <= 0):
                price_value = "-"
            item = QTableWidgetItem()
            item.setData(Qt.EditRole, price_value)
            table.setItem(i, 3, item)
            
            cleaned_rad_price = rad_price
            if (rad_price <= 0 or rad_price > 100000):
                cleaned_rad_price = "-"
            item = QTableWidgetItem()
            item.setData(Qt.EditRole, cleaned_rad_price)
            table.setItem(i, 4, item)
            
            item = QTableWidgetItem()
            item.setData(Qt.EditRole, rad_income)
            table.setItem(i, 5, item)
            
            price_value = ((rad_income * 4) - rad_price) / 4
            if (price_value <= 0):
                price_value = "-"
            item = QTableWidgetItem()
            item.setData(Qt.EditRole, price_value)
            table.setItem(i, 6, item)  

        table.sortByColumn(6, Qt.DescendingOrder)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table