#!-*- coding:utf-8 -*-
import os
import sys

from PyQt5 import uic
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QDialog, QApplication, QListWidgetItem, QScrollArea

from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize,
                          Qt, QTime, QTimer, QUrl)
from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtWidgets import (QAction, qApp, QApplication, QDialog, QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
                             QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy, QStyleFactory,
                             QVBoxLayout, QWidget, QScrollBar, QSlider)



class scalableTimeline(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.sliderBaseWidth = 770
        self.factor = 1
        self.factor_maximum = 16
        scrollAreaLayout = QVBoxLayout(self)

        self.scrollBar = QScrollBar()
        self.scrollBar.setOrientation(Qt.Horizontal)
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setFixedSize(self.sliderBaseWidth, 10)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.slider)
        self.scrollArea.setAlignment(Qt.AlignVCenter)
        scrollAreaLayout.addWidget(self.scrollArea)

        buttonLayout = QHBoxLayout(self)
        buttton_plus = QPushButton()
        buttton_plus.setText('+')
        buttton_minus = QPushButton()
        buttton_minus.setText('-')
        self.label_factor = QLabel()
        self.label_factor.setText('1')
        buttonLayout.addWidget(buttton_plus)
        buttonLayout.addWidget(buttton_minus)
        buttonLayout.addWidget(self.label_factor)

        buttton_plus.clicked.connect(self.increaseSliderWidth)
        buttton_minus.clicked.connect(self.decreaseSliderWidth)

        scrollAreaLayout.addLayout(buttonLayout)

        self.setLayout(scrollAreaLayout)
        self.setGeometry(200, 200, 800, 20)
        self.setWindowTitle('Slider Scroll Text')
        self.show()

    def clip(self, val, min_, max_):
        return min_ if val < min_ else max_ if val > max_ else val

    def increaseSliderWidth(self):
        if self.factor == 1:
            self.factor += 1
        else:
            self.factor += 2
        self.factor = self.clip(self.factor, 1, self.factor_maximum)
        self.label_factor.setText(str(self.factor))
        self.slider.setFixedWidth(self.factor * self.sliderBaseWidth)

    def decreaseSliderWidth(self):
        if self.factor == 2:
            self.factor -= 1
        else:
            self.factor -= 2
        self.factor = self.clip(self.factor, 1, self.factor_maximum)
        self.label_factor.setText(str(self.factor))
        self.slider.setFixedWidth(self.factor * self.sliderBaseWidth)

class SliderInsideScroll(QScrollBar):
    pass


def main():
   app = QApplication(sys.argv)
   dialog = scalableTimeline()
   dialog.show()
   app.exec_()


if __name__ == '__main__':
   main()