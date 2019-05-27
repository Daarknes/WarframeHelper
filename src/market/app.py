from PyQt5.Qt import Qt
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QTableWidget, QTableWidgetItem, QTabWidget, QHeaderView

from core import constants, wfmarket_v2
from market import instance


def calc_profit(sell_price, buy_price):
    if not sell_price or not buy_price:
        return None
    else:
        return sell_price - buy_price


class Window(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        
        self.setWindowTitle("Warframe Market Helper")
        self.setWindowIcon(QIcon(constants.res_loc() + "relic.png"))
        self.resize(QSize(1200, 700))
        self.setupUi()
    
    def setupUi(self):
        wTabs = QTabWidget()
        self.setCentralWidget(wTabs)
        
        table_sets = []
        table_single = []

        for cat_data in wfmarket_v2.get_item_data().values():
            for item_name, item_data in cat_data.items():
                item_prices = wfmarket_v2.get_prices(item_data['url_name'])
                item_sell_repr = instance.config["calc_sell_repr"](item_prices)
    
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
                    
                    comp_sell_repr = instance.config["calc_component_repr"](component_prices, "sell")
                    comp_buy_repr = instance.config["calc_component_repr"](component_prices, "buy")
                    
                    table_sets.append({'Name': item_name, 'Components': ", ".join(map(str, components)),
                                       'Set (Sell)': item_sell_repr, 'Components (Sell)': comp_sell_repr, 'Components (Buy)': comp_buy_repr,
                                       'Potential Profit': calc_profit(item_sell_repr, comp_buy_repr)})
                else:
                    item_buy_repr = instance.config["calc_buy_repr"](item_prices)
                    table_single.append({'Name': item_name, 'Sell': item_sell_repr, 'Buy': item_buy_repr, 'Potential Profit': calc_profit(item_sell_repr, item_buy_repr)})

        if table_sets:
            wTabs.addTab(self.createTable(table_sets), "Sets")
        if table_single:
            wTabs.addTab(self.createTable(table_single), "Single Items")
        
#         wTabs.addTab(self.createRelicTable(market_names), "Relics")

    def createTable(self, table_list):
        headers = table_list[0].keys()

        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setRowCount(len(table_list))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().hide()

        for i, entry in enumerate(table_list):
            for j, header in enumerate(headers):
                item = QTableWidgetItem()
                item.setData(Qt.EditRole, entry[header])
                table.setItem(i, j, item)

        table.sortByColumn(len(headers)-1, Qt.DescendingOrder)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    
#     def createRelicTable(self, market_names):
#         relic_prices = wfmarket.get_all(wfmarket.CAT_RELICS)
#         item_prices = wfmarket.get_all(wfmarket.CAT_ITEMS)
#         
#         # 0: intact income
#         # 1: intact price
#         # 2: radiant income
#         # 3: radiant price
#         table = QTableWidget()
#         table.setColumnCount(7)
#         table.setRowCount(len(market_names["relics"]))
#         table.setHorizontalHeaderLabels(["Name", "Price Intact", "Potential Profit Intact", "Profit 4 Pers Rad from Intact", "Price Radiant", "Potential Profit Radiant", "Profit 4 Pers Rad from Radiant"])
#         table.verticalHeader().hide()
#         
#         for i, (relic_name, relic_data) in enumerate(market_names["relics"].items()):
#             row = ["-"] * 4
#             
#             for j, (relic_type, components) in enumerate(relic_data.items()):
#                 relic_price = relic_prices[relic_name + "_" + relic_type]
#                 if relic_price is None: # if we have no data for this relic, we don't want to show it
#                     continue
#             
# #                buy_repr = instance.config["calc_buy_repr"](relic_price)
#                 sell_repr = instance.config["calc_sell_repr"](relic_price)
#                 
# #                if buy_repr is None:
# #                    buy_repr = 9999999
# #                else:
# #                    invalid_flag = False
#                 
#                 if sell_repr is None:
#                     continue
#                     
#                 # best_relic_price = min(buy_repr, sell_repr)
#                 best_relic_price = sell_repr # a lot of people try to buy relics way too cheap
#                 
#                 
#                 if best_relic_price <= 0:
#                     continue # We can't buy this relic, so we can skip it
#                 
#                 income = 0
#                 
#                 #calculate the expected income for the current relic
#                 for component_name, component_probability in components:
#                     current_price = item_prices[component_name]
#                 
#                     if current_price is None:
#                         continue
#                 
#                     buy_repr = instance.config["calc_buy_repr"](current_price)
#                     sell_repr = instance.config["calc_sell_repr"](current_price)
#                     
#                     if buy_repr and sell_repr:
#                         best_item_price = max(buy_repr, sell_repr)
#                     elif not (buy_repr or sell_repr):
#                         continue
#                     else:
#                         best_item_price = buy_repr or sell_repr
#                     
#                     income += best_item_price * component_probability
#                 
#                 row[2*j] = income
#                 row[2*j+1] = best_relic_price
# 
# 
#             # TODO: make this prettier
#             table.setItem(i, 0, QTableWidgetItem(" ".join(relic_name.split("_"))))
#             
#             item = QTableWidgetItem()
#             item.setData(Qt.EditRole, row[0])
#             table.setItem(i, 1, item)
#             
#             item = QTableWidgetItem()
#             item.setData(Qt.EditRole, row[1])
#             table.setItem(i, 2, item)
#             
#             if row[2] != "-" and row[1] != "-":
#                 price_value = row[2] * 4 - row[1]
#             else:
#                 price_value = "-"
#             item = QTableWidgetItem()
#             item.setData(Qt.EditRole, price_value)
#             table.setItem(i, 3, item)
#             
#             item = QTableWidgetItem()
#             item.setData(Qt.EditRole, row[3])
#             table.setItem(i, 4, item)
#             
#             item = QTableWidgetItem()
#             item.setData(Qt.EditRole, row[2])
#             table.setItem(i, 5, item)
#             
#             if row[2] != "-" and row[3] != "-":
#                 price_value = row[2] * 4 - row[3]
#             else:
#                 price_value = "-"
#             item = QTableWidgetItem()
#             item.setData(Qt.EditRole, price_value)
#             table.setItem(i, 6, item)  
# 
#         table.sortByColumn(6, Qt.DescendingOrder)
#         table.setSortingEnabled(True)
#         table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
#         return table
