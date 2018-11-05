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
import time
from PyQt5.QtGui import QPalette, QColor


hotkey = "alt+m"
# saves the screenshot to the 'images/'-folder when the hotkey is pressed (debug)
save_screenshot = True


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
        self.setWindowTitle("Warframe Market Prices")
#        self.setWindowIcon(QIcon(constants.program + "logo.png"))
        self.resize(QSize(800, 500))

        dummy = QWidget()
        mainLayout = QVBoxLayout(dummy)
        mainLayout.setSpacing(20)
        self.setCentralWidget(dummy)
        
        lDesc = QLabel("Press '{}' to search for prices (you need to be in the relic reward screen)".format(hotkey))
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

    def setLabelText(self, *texts):
        for label, text in zip(self.labels, texts):
            label.setText(text)


class KeyboardThread(QThread):
    def run(self):
        while True:
            keyboard.wait(hotkey)
            
            try:
                hwnd = win32gui.FindWindow(None, r'Warframe')
                win32gui.SetForegroundWindow(hwnd)
                if win32gui.GetForegroundWindow() != hwnd:
                    raise Exception("Could not set the Warframe window as foreground")
                x1, y1, x2, y2 = win32gui.GetClientRect(hwnd)
                x1, y1 = win32gui.ClientToScreen(hwnd, (x1, y1))
                x2, y2 = win32gui.ClientToScreen(hwnd, (x2, y2))
            except:
                print("could not find and focus the Warframe window. Stacktrace:\n", traceback.print_exc(file=sys.stdout))
                return
            
            image = ImageGrab.grab((x1, y1, x2, y2))            
            if save_screenshot:
                if not os.path.exists("../images/"):
                    os.makedirs("../images/")
                image.save("../images/{}.png".format(datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")))

            item_names = warframe_ocr.get_item_names(image)
            print("[Main] item names: ", item_names)
            if not item_names:
                for label in window.labels:
                    label.setText("Error (Could not find item names)")
                return
             
            item_prices = wfmarket.item_names_to_prices_map(item_names)
            bestLabel = None
            best_mean = 0

            offset = 1 if len(item_names) <= 2 else 0
            for i, label in enumerate(window.labels):
                if 0 <= i-offset < len(item_names):
                    text = item_names[i - offset] + "\n\n"
                    prices = item_prices[item_names[i - offset]]
                    
                    if prices is None:
                        text += "ERROR"
                    elif len(prices) == 0:
                        text += "Not sellable"
                    else:
                        mean = sum(prices) / len(prices)
                        if mean > best_mean:
                            best_mean = mean
                            bestLabel = label
                        text += "\n".join(map(str, prices))
                else:
                    text = " - "

                label.setText(text)
                label.setPalette(window.labelDefaultPalette)
            
            bestLabel.setPalette(window.labelBestPalette)

if __name__ == "__main__":
    # to show exceptions from Qt after crash
    sys.excepthook = excepthook
    
    app = QApplication(sys.argv)
    window = Window()
    keyboardThread = KeyboardThread()
    
    window.show()
    keyboardThread.start()
    sys.exit(app.exec_())
