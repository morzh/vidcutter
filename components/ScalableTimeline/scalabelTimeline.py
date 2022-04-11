#!-*- coding:utf-8 -*-
import os
import sys

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QApplication, QListWidgetItem

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
        vbox = QVBoxLayout(self)
        vbox2 = QVBoxLayout(self)
        self.scrollBar = QScrollBar()
        self.scrollBar.setOrientation(Qt.Horizontal)
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setFixedSize(1000, 10)
        vbox2.addWidget(self.slider)
        self.scrollBar.setLayout(vbox2)
        vbox.addWidget(self.scrollBar)
        self.setLayout(vbox)

        self.setGeometry(200, 200, 800, 150)
        self.setWindowTitle('QListWidget')
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