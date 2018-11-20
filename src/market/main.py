from _io import StringIO
import ctypes
import platform
import sys
import traceback
import os

if __name__ == "__main__":
    from core.config import Config
    
    config = Config()
    
    section_market = config.addSection("Warframe Market")
    section_market.addEntry("MAX_ORDER_AGE", 24, "only include orders of players that are either in-game, or that have been updated in the last X hours (DEFAULT: 24)")
    section_market.addEntry("MAX_UPDATE_AGE", 24, "The local market data (the prices) gets updated after this amount of hours (DEFAULT: 24)")
    
    config.build()
    config.loadAndUpdate(os.path.join(os.path.dirname(__file__), "config.cfg"))
#     instance.setConfig(config)

    # load (and possibly update) warframe market
    from core import wfmarket
    wfmarket.load(config["MAX_UPDATE_AGE"], config["MAX_ORDER_AGE"])

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
