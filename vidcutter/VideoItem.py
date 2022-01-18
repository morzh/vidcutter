from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize, Qt, QTextStream, QTime, QTimer, QUrl)

class VideoItem:
    def __init__(self):
        self.thumb = QPixmap()
        self.filepath = ''
        self.description = ''
