from _io import StringIO
import ctypes
import platform
import sys
import traceback

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    from app import Window
    import warframe_ocr


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
