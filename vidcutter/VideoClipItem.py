from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize,
                          Qt, QTextStream, QTime, QTimer, QUrl)

class VideoClipItem:
    def __init__(self):
        self.timeStart = QTime()
        self.timeEnd = QTime()
        self.thumb = QPixmap()
        self.clipName = ''
        self.clipClass = ''  # for future challenges
        self.visibility = True
