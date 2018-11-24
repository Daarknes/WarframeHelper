from _io import StringIO
import ctypes
import platform
import sys
import traceback
import os

from core.config import Config
from relicrewards import instance
config = Config()

section_ocr = config.addSection("OCR")
section_ocr.addEntry("TESSERACT_PATH", r"C:\Program Files\Tesseract\tesseract.exe", "Path to your tesseract.exe")

section_market = config.addSection("Warframe Market")
section_market.addEntry("MAX_CONNECTIONS", 100, "The maximum number of simultaneous threads for http-requests (DEFAULT: 100)")
section_market.addEntry("MAX_ORDER_AGE", 12, "only include orders of players that are either in-game, or that have been updated in the last X hours (DEFAULT: 12)")
section_market.addEntry("MAX_UPDATE_AGE", 24, "The local market data (the prices) gets updated after this amount of hours (DEFAULT: 24)")

section_gui = config.addSection("GUI")
section_gui.addEntry("HOTKEY", "alt+m", "The hotkey to press (DEFAULT: 'alt+m')")
section_gui.addEntry("save_screenshot", True, "Saves the screenshot to the 'images/'-folder when the hotkey is pressed (debug) (DEFAULT: True)")

config.build()
config.loadAndUpdate(os.path.join(os.path.dirname(__file__), "config.cfg"))
instance.setConfig(config)

if __name__ == "__main__":
    # load (and possibly update) warframe market
    from core import wfmarket
    wfmarket.load(config["MAX_CONNECTIONS"], config["MAX_UPDATE_AGE"], config["MAX_ORDER_AGE"])

    from PyQt5.QtWidgets import QApplication
    from relicrewards.app import Window
    from relicrewards import warframe_ocr


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
        appId = u'warframe_relic_reward_helper'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
    
    window = Window()
    warframe_ocr.init()
    window.show()
    
    exitCode = application.exec_()
    warframe_ocr.cleanup()
    sys.exit(exitCode)
