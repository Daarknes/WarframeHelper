from _io import StringIO
import ctypes
import platform
import sys
import traceback

from core.config import Config
from relicrewards import instance
from core import constants
_config = Config()

section_ocr = _config.addSection("OCR")
section_ocr.addEntry("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe", "Path to your tesseract.exe")

section_gui = _config.addSection("GUI")
section_gui.addEntry("HOTKEY", "alt+m", "The hotkey to press")
section_gui.addEntry("save_screenshot", True, "Saves the screenshot to the 'images/'-folder when the hotkey is pressed (debug)")

_config.build()
_config.loadAndUpdate(constants.CONFIG_LOC + "relicrewardhelper.cfg")
instance.setConfig(_config)

if __name__ == "__main__":
    # load (and possibly update) warframe market
    from core import wfmarket_v2
    wfmarket_v2.load()

    from PyQt5.QtWidgets import QApplication
    from relicrewards.app import Window
    from relicrewards import warframe_ocr

    # we need to call this when we updated the item data    
#     warframe_ocr.update_item_data()


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
