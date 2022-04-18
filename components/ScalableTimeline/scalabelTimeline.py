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
        scrollAreaLayout = QVBoxLayout(self)

        self.scrollBar = QScrollBar()
        self.scrollBar.setOrientation(Qt.Horizontal)
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setFixedSize(1800, 10)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.slider)
        self.scrollArea.setAlignment(Qt.AlignVCenter)
        scrollAreaLayout.addWidget(self.scrollArea)

        buttonLayout = QHBoxLayout(self)
        buttton_plus = QPushButton()
        buttton_plus.setText('+')
        buttton_minus = QPushButton()
        buttton_minus.setText('-')
        buttonLayout.addWidget(buttton_plus)
        buttonLayout.addWidget(buttton_minus)

        scrollAreaLayout.addLayout(buttonLayout)

        self.setLayout(scrollAreaLayout)
        self.setGeometry(200, 200, 800, 20)
        self.setWindowTitle('Slider Scroll Text')
        self.show()


class SliderInsideScroll(QScrollBar):
    pass


def main():
   app = QApplication(sys.argv)
   dialog = scalableTimeline()
   dialog.show()
   app.exec_()


if __name__ == '__main__':
   main()