#!-*- coding:utf-8 -*-
import os
import sys
import logging

from PyQt5 import uic
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QScrollArea

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel,QPushButton, QVBoxLayout, QWidget, QScrollBar, QSlider, QLineEdit)


class scalableTimeline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        # self.theme = self.parent.theme

        self.sliderBaseWidth = 770
        self.factor = 1
        self.factor_maximum = 16
        scrollAreaLayout = QVBoxLayout(self)

        # self.scrollBar = QScrollBar()
        # self.scrollBar.setOrientation(Qt.Horizontal)
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setFixedSize(self.sliderBaseWidth, 10)
        # self.slider.setTickInterval(self.sliderBaseWidth)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.slider)
        self.scrollArea.setAlignment(Qt.AlignVCenter)
        scrollAreaLayout.addWidget(self.scrollArea)

        buttonLayout = QHBoxLayout(self)
        butttonPlus = QPushButton()
        butttonPlus.setText('+')

        butttonMinus = QPushButton()
        butttonMinus.setText('-')

        buttonMaximum = QPushButton()
        buttonMaximum.setText('Max')
        buttonMaximum.clicked.connect(self.on_maximumButtonPressed)

        rangeWidthEdit = QLineEdit()
        rangeWidthEdit.setFixedWidth(120)
        rangeWidthEdit.textChanged[str].connect(self.on_widthChanged)
        rangeWidthLabel = QLabel()
        rangeWidthLabel.setText('Width')

        rangeMinimumEdit = QLineEdit()
        rangeMinimumEdit.setFixedWidth(120)
        rangeMinimumEdit.textChanged[str].connect(self.on_rangeMinimumChanged)
        rangeMinimumLabel = QLabel()
        rangeMinimumLabel.setText('Range min')

        rangeMaximumEdit = QLineEdit()
        rangeMaximumEdit.setFixedWidth(120)
        rangeMaximumEdit.textChanged[str].connect(self.on_rangeMaximumChanged)
        rangeMaximumLabel = QLabel()
        rangeMaximumLabel.setText('Range max')

        self.label_factor = QLabel()
        self.label_factor.setText('1')
        self.label_factor.setAlignment(Qt.AlignCenter)


        buttonLayout.addWidget(butttonMinus)
        buttonLayout.addWidget(self.label_factor)
        buttonLayout.addWidget(butttonPlus)


        butttonPlus.clicked.connect(self.increaseSliderWidth)
        butttonMinus.clicked.connect(self.decreaseSliderWidth)

        scrollAreaLayout.addLayout(buttonLayout)

        self.setLayout(scrollAreaLayout)
        self.setGeometry(200, 200, 800, 20)
        self.setWindowTitle('Slider Scroll Text')
        self.show()


    def on_widthChanged(self, width):
        try:
            self.slider.setFixedWidth(int(width))
        except:
            print('''Can't set width value of''', value)
    def on_rangeMinimumChanged(self, value: str):
        try:
            self.slider.setMinimum(int(value))
        except:
            print('''Can't set minimum value of''', value)

    def on_rangeMaximumChanged(self, value: str):
        try:
            self.slider.setMaximum(int(value))
        except:
            print('''Can't set maximum value of''', value)

    def on_maximumButtonPressed(self):
        self.slider.setValue(self.slider.maximum())

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
        self.slider.setMaximum(self.factor * self.sliderBaseWidth)

    def decreaseSliderWidth(self):
        if self.factor == 2:
            self.factor -= 1
        else:
            self.factor -= 2
        self.factor = self.clip(self.factor, 1, self.factor_maximum)
        self.label_factor.setText(str(self.factor))
        self.slider.setFixedWidth(self.factor * self.sliderBaseWidth)
        self.slider.setMaximum(self.factor * self.sliderBaseWidth)


class SliderInsideScroll(QScrollBar):
    pass


def main():
    app = QApplication(sys.argv)
    dialog = scalableTimeline()
    dialog.show()
    app.exec_()


if __name__ == '__main__':
    main()
