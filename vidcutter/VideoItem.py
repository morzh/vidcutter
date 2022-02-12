from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize, Qt, QTextStream, QTime, QTimer, QUrl)
from vidcutter.VideoClipItem import VideoClipItem

class VideoItem:
    def __init__(self, *args):
        if not len(args):
            self._thumbnail = QPixmap()
            self._duration = QTime()
            self._filepath = ''
            self.description = ''
            self.clips = []
            self._currentCLipIndex = 0
        elif len(args) == 2:
            self.thumb = args[0]
            self.filename = args[1]


    def clipsLast(self):
        if len(self.clips):
            return self.clips[-1]
        else:
            raise Exception

    def clipsLength(self):
        return len(self.clips)

    @property
    def filename(self):
        return self._filepath

    @filename.setter
    def filename(self, fp: str):
        self._filepath = fp

    @property
    def thumbnail(self):
        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, thumb: QPixmap):
        self._thumbnail = thumb

    @property
    def currentClipIndex(self):
        return self._currentCLipIndex

    @currentClipIndex.setter
    def currentClipIndex(self, index: int):
        if index < 0:
            index *= -1
        self._currentCLipIndex = index

    @property
    def duration(self, time: QTime):
        self._duration = time

    @duration.setter
    def duration(self, time: QTime):
        self._duration = time
