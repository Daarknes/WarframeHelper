from datetime import datetime
import os

from PIL import ImageGrab
from PyQt5 import QtCore
from PyQt5.QtCore import QSize, QThread
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QSizePolicy, QHBoxLayout, QFrame
import keyboard
import win32gui

from relicrewards import instance, warframe_ocr
from core import constants, wfmarket_v2
from PyQt5.Qt import Qt
import traceback
import time


price_quantile = 0.3
PATH_IMAGES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "images")) + os.path.sep

class Window(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        
        self.setWindowTitle("Warframe Relic Reward Helper")
        self.setWindowIcon(QIcon(constants.res_loc() + "relic.png"))
        self.resize(QSize(1100, 900))
        self.setupUi()
        
        keyboardThread = KeyboardThread(self)
        keyboardThread.textSignal.connect(self.setLabelText)
        keyboardThread.paletteSignal.connect(self.setLabelPalette)
        keyboardThread.start()
    
    def setupUi(self):
        dummy = QWidget()
        mainLayout = QVBoxLayout(dummy)
        mainLayout.setSpacing(20)
        self.setCentralWidget(dummy)
        
        lDesc = QLabel("Press '{}' to search for prices (you need to be in the relic reward screen)".format(instance.config["HOTKEY"]))
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
            keyboard.wait(instance.config["HOTKEY"])
            
            try:
                hwnd = win32gui.FindWindow(None, r"Warframe")
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
                if win32gui.GetForegroundWindow() != hwnd:
                    raise Exception("Could not set the Warframe window as foreground")
                x1, y1, x2, y2 = win32gui.GetClientRect(hwnd)
                x1, y1 = win32gui.ClientToScreen(hwnd, (x1, y1))
                x2, y2 = win32gui.ClientToScreen(hwnd, (x2, y2))
            except:
                print("could not find and focus the Warframe window. Stacktrace:")
                traceback.print_exc()
                continue
            
            for i in range(4):
                self.textSignal.emit(i, "...")
                self.paletteSignal.emit(i, False)
            
            image = ImageGrab.grab((x1, y1, x2, y2))   
            if instance.config["save_screenshot"]:
                if not os.path.exists(PATH_IMAGES):
                    os.makedirs(PATH_IMAGES)
                image.save(PATH_IMAGES + str(datetime.now().strftime("%d-%m-%Y_%H-%M-%S")) + ".png")

            item_names, ducat_values = warframe_ocr.get_item_names(image)
            print("[Main] item names:", list(item_names), "ducat values:", ducat_values)
            if not item_names:
                for i in range(4):
                    self.textSignal.emit(i, "Error (Could not find item names)")
                continue
            
            
            item_prices = {}
            for item_name in set(item_names):
                try:
                    prices = wfmarket_v2.get_prices(item_name)
                except:
                    prices = None

                if prices is None:
                    item_prices[item_name] = None
                else:
                    item_prices[item_name] = prices['sell']
        

            bestLabel = None
            best_quantile = 0

            offset = 1 if len(item_names) <= 2 else 0
            for i in range(4):
                if 0 <= i-offset < len(item_names):
                    item_name = item_names[i - offset]
                    text = item_name + "\nDucats: " + (str(ducat_values[i - offset]) if ducat_values[i - offset] else "-") + "\n\n"
                    prices = item_prices[item_names[i - offset]]

                    if not prices:
                        text += "ERROR / Not sellable"
                    else:
                        quantile = prices[int(price_quantile * len(prices))]
                        if quantile > best_quantile:
                            best_quantile = quantile
                            bestLabel = i

                        num_lines = min(len(prices), 40)
                        text += "\n".join(map(str, prices[:num_lines]))
                else:
                    text = " - "

                self.textSignal.emit(i, text)
            
            if bestLabel is not None:
                self.paletteSignal.emit(bestLabel, True)
