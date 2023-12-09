#!-*- coding:utf-8 -*-
import os
import sys
import logging

from PyQt5 import uic
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QDialog, QApplication, QListWidgetItem, QScrollArea

from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize,
                          Qt, QTime, QTimer, QUrl)
from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtWidgets import (QAction, qApp, QApplication, QDialog, QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
                             QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy, QStyleFactory,
                             QVBoxLayout, QWidget, QScrollBar, QSlider, QLineEdit)


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

        self.scrollBar = QScrollBar()
        self.scrollBar.setOrientation(Qt.Horizontal)
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setFixedSize(self.sliderBaseWidth, 10)
        self.slider.setRange(0, 504641)
        self.slider.setFixedWidth(4736)
        # self.slider.setTickInterval(self.sliderBaseWidth)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.slider)
        self.scrollArea.setAlignment(Qt.AlignVCenter)
        scrollAreaLayout.addWidget(self.scrollArea)

        buttonLayout = QHBoxLayout(self)
        buttonMaximum = QPushButton()
        buttonMaximum.setText('Max')
        buttonMaximum.clicked.connect(self.on_maximumButtonPressed)

        rangeWidthEdit = QLineEdit()
        rangeWidthEdit.setFixedWidth(120)
        rangeWidthEdit.setText('4736')
        rangeWidthEdit.textChanged[str].connect(self.on_widthChanged)
        rangeWidthLabel = QLabel()
        rangeWidthLabel.setText('Slider.width')

        rangeMinimumEdit = QLineEdit()
        rangeMinimumEdit.setFixedWidth(120)
        rangeMinimumEdit.setText('0')
        rangeMinimumEdit.textChanged[str].connect(self.on_rangeMinimumChanged)
        rangeMinimumLabel = QLabel()
        rangeMinimumLabel.setText('Slider.min')

        rangeMaximumEdit = QLineEdit()
        rangeMaximumEdit.setFixedWidth(120)
        rangeMaximumEdit.setText('504641')
        rangeMaximumEdit.textChanged[str].connect(self.on_rangeMaximumChanged)
        rangeMaximumLabel = QLabel()
        rangeMaximumLabel.setText('Slider.max')

        self.label_factor = QLabel()
        self.label_factor.setText('1')

        buttonLayout.addWidget(rangeWidthLabel)
        buttonLayout.addWidget(rangeWidthEdit)
        buttonLayout.addWidget(rangeMinimumLabel)
        buttonLayout.addWidget(rangeMinimumEdit)
        buttonLayout.addWidget(rangeMaximumLabel)
        buttonLayout.addWidget(rangeMaximumEdit)
        buttonLayout.addWidget(buttonMaximum)

        scrollAreaLayout.addLayout(buttonLayout)

        self.setLayout(scrollAreaLayout)
        self.setGeometry(200, 200, 800, 20)
        self.setWindowTitle('Slider Scroll Text')
        self.show()


    def on_widthChanged(self, width: str):
        try:
            self.slider.setFixedWidth(int(width))
        except:
            print('''Can't set width value of''', width)
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


def main():
    app = QApplication(sys.argv)
    dialog = scalableTimeline()
    dialog.show()
    app.exec_()


if __name__ == '__main__':
    main()
