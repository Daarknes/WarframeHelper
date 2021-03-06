from _io import StringIO
import ctypes
import platform
import sys
import traceback
import os


from core.config import Config, FunctionBlock
from core import constants
from market import instance

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
config.loadAndUpdate(os.path.join(constants.CONFIG_LOC, "markethelper.cfg"))
instance.setConfig(config)
    
if __name__ == "__main__":
    # load (and possibly update) warframe market
    from core import wfmarket_v2
    wfmarket_v2.load()

    from PyQt5.QtWidgets import QApplication
    from market.app import Window


def excepthook(excType, excValue, tracebackobj):
    """
    Global function to catch unhandled exceptions.
    @param excType exception type
    @param excValue exception value
    @param tracebackobj traceback object
    """
    separator = '-' * 80

    tbinfofile = StringIO()
    traceback.print_tb(tracebackobj, None, tbinfofile)
    tbinfofile.seek(0)
    tbinfo = tbinfofile.read()
    errmsg = '%s: \n%s' % (str(excType), str(excValue))
    sections = [separator, errmsg, separator, tbinfo]
    msg = '\n'.join(sections)
    sys.exit(str(msg))

if __name__ == "__main__":
    # to show exceptions from Qt after crash
    sys.excepthook = excepthook
    
#     signal.signal(signal.SIGINT, signal.SIG_DFL)
    application = QApplication(sys.argv)
    if platform.system() == "Windows":
        appId = u'warframe_market_helper'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
    
    window = Window()
    window.show()
    
    exitCode = application.exec_()
    sys.exit(exitCode)
