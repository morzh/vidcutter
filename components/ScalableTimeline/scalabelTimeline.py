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
        vbox = QVBoxLayout(self)
        vbox2 = QVBoxLayout(self)
        self.scrollBar = QScrollBar()
        self.scrollBar.setOrientation(Qt.Horizontal)
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setFixedSize(1800, 10)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.slider)
        self.scrollArea.setAlignment(Qt.AlignVCenter)
        vbox.addWidget(self.scrollArea)

        # self.slider.setSizePolicy(QSizePolicy.Frame, QSizePolicy.Fixed)
        '''
        
        vbox2.addWidget(self.slider)
        vbox2.setGeometry(QRect(0, 0, 1800, 100))
        self.scrollBar.setLayout(vbox2)
        self.scrollBar.setFixedSize(600, 30)
        vbox.addWidget(self.scrollBar)
        self.setLayout(vbox)
        '''
        self.setLayout(vbox)
        self.setGeometry(200, 200, 800, 20)
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