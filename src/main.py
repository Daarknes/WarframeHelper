from _io import StringIO
from builtins import Exception
import datetime
import os
import sys
import traceback

from PIL import ImageGrab
from PyQt5.Qt import Qt, QSizePolicy, QFont
from PyQt5.QtCore import QThread, QSize
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel, QFrame, QVBoxLayout
import keyboard
import win32gui

import warframe_ocr
import wfmarket
from PyQt5.QtGui import QPalette, QColor, QIcon
import platform
import ctypes
import config
from PyQt5 import QtCore


price_quantile = 0.3

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
    

class Window(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("Warframe Relic Reward Helper")
        self.setWindowIcon(QIcon(os.path.join("..", "res", "logo.png")))
        self.resize(QSize(1200, 700))

        dummy = QWidget()
        mainLayout = QVBoxLayout(dummy)
        mainLayout.setSpacing(20)
        self.setCentralWidget(dummy)
        
        lDesc = QLabel("Press '{}' to search for prices (you need to be in the relic reward screen)".format(config.HOTKEY))
        lDesc.setFont(QFont("Monospace", 14))
        lDesc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lDesc.setAlignment(Qt.AlignHCenter)
        mainLayout.addWidget(lDesc)
        
        labelLayout = QHBoxLayout()
        mainLayout.addLayout(labelLayout)

        # labels for the 4 rewards
        self.labels = []
        labelFont = QFont("Monospace", 12)
        self.labelBestPalette = QPalette(QColor(150, 255, 150))
        self.labelDefaultPalette = QPalette(Qt.white)
        
        for _ in range(4):
            label = QLabel(" - ")
            label.setFont(labelFont)
            label.setAlignment(Qt.AlignHCenter)
            label.setFrameShape(QFrame.Panel)
            label.setFrameShadow(QFrame.Sunken)
            label.setAutoFillBackground(True)
            label.setPalette(self.labelDefaultPalette)
            
            self.labels.append(label)
            labelLayout.addWidget(label)
    
    @QtCore.pyqtSlot(int, str)
    def setLabelText(self, lId, text):
        self.labels[lId].setText(text)
    
    @QtCore.pyqtSlot(int, bool)
    def setLabelPalette(self, lId, best):
        if best:
            self.labels[lId].setPalette(self.labelBestPalette)
        else:
            self.labels[lId].setPalette(self.labelDefaultPalette)

class KeyboardThread(QThread):
    textSignal = QtCore.pyqtSignal(int, str)
    paletteSignal = QtCore.pyqtSignal(int, bool)
    
    def run(self):
        while True:
            keyboard.wait(config.HOTKEY)
            
            try:
                hwnd = win32gui.FindWindow(None, r'Fotos')
                win32gui.SetForegroundWindow(hwnd)
                if win32gui.GetForegroundWindow() != hwnd:
                    raise Exception("Could not set the Warframe window as foreground")
                x1, y1, x2, y2 = win32gui.GetClientRect(hwnd)
                x1, y1 = win32gui.ClientToScreen(hwnd, (x1, y1))
                x2, y2 = win32gui.ClientToScreen(hwnd, (x2, y2))
            except:
                print("could not find and focus the Warframe window. Stacktrace:\n", traceback.print_exc(file=sys.stdout))
                return
            
            for i in range(4):
                self.textSignal.emit(i, "...")
                self.paletteSignal.emit(i, False)
            
            image = ImageGrab.grab((x1, y1, x2, y2))   
            if config.save_screenshot:
                if not os.path.exists("../images/"):
                    os.makedirs("../images/")
                image.save("../images/{}.png".format(datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")))

            item_names = warframe_ocr.get_item_names(image)
            print("[Main] item names: ", item_names)
            if not item_names:
                for i in range(4):
                    self.textSignal.emit(i, "Error (Could not find item names)")
                return
             
            item_prices = wfmarket.item_names_to_prices_map(item_names)
            bestLabel = None
            best_quantile = 0

            offset = 1 if len(item_names) <= 2 else 0
            for i in range(4):
                if 0 <= i-offset < len(item_names):
                    text = item_names[i - offset] + "\n\n"
                    prices = item_prices[item_names[i - offset]]
                    
                    if prices is None:
                        text += "ERROR"
                    elif len(prices) == 0:
                        text += "Not sellable"
                    else:
                        quantile = prices[int(price_quantile * len(prices))]
                        if quantile > best_quantile:
                            best_quantile = quantile
                            bestLabel = i

                        num_lines = min(len(prices), 30)
                        text += "\n".join(map(str, prices[:num_lines]))
                else:
                    text = " - "

                self.textSignal.emit(i, text)
            
            self.paletteSignal.emit(bestLabel, True)

if __name__ == "__main__":
    # to show exceptions from Qt after crash
    sys.excepthook = excepthook
    
    app = QApplication(sys.argv)
    if platform.system() == "Windows":
        appId = u'warframe_relic_reward_helper'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
    
    window = Window()
    keyboardThread = KeyboardThread(window)
    keyboardThread.textSignal.connect(window.setLabelText)
    keyboardThread.paletteSignal.connect(window.setLabelPalette)
    
    window.show()
    keyboardThread.start()
    sys.exit(app.exec_())
