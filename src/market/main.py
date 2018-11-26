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
section_funcs.addEntry("calc_sell_repr", FunctionBlock(r'''if not prices:
    return None
else:
    # take 0.3 quantile for selling representative
    return prices[int(0.3 * len(prices))]''', "prices"), "calculates a sell-price-representative from price-data")

section_funcs.addEntry("calc_buy_repr", FunctionBlock(r'''if not prices:
    return None
else:
    # for buying only include the cheapest 4
    return sum(prices[:10]) // len(prices[:10])''', "prices"), "calculates a buy-price-representative from price-data")

section_funcs.addEntry("calc_component_repr", FunctionBlock(r'''comp_repr = 0
for comp_name in component_names:
    if prices[comp_name] is None:
        return None
    comp_prices = prices[comp_name][order_type]

    buy_repr = calc_buy_repr(comp_prices)
    if buy_repr is None:
        return None

    comp_repr += buy_repr
return comp_repr''', "prices, component_names, order_type"), "calculates a buy-price-representative from price-data")

config.build()
config.loadAndUpdate(os.path.join(constants.CONFIG_LOC, "markethelper.cfg"))
instance.setConfig(config)
    
if __name__ == "__main__":
    # load (and possibly update) warframe market
    from core import wfmarket
    wfmarket.load()

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
