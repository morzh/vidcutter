from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize,
                          Qt, QTextStream, QTime, QTimer, QUrl)

class VideoClipItem:
    def __init__(self, *args):
        if not len(args):
            self._timeStart = QTime()
            self._timeEnd = QTime()
            self._thumbnail = QPixmap()
            self._clipName = ''
            self._visibility = True
            self.clipClass = 'squat'  # for future challenges

        if len(args) == 4:
            self.timeStart = args[0]
            self.timeEnd = args[1]
            self.thumb = args[2]
            self.clipName = args[3]

    @property
    def timeStart(self) -> QTime:
        return self._timeStart

    @property
    def timeEnd(self) -> QTime:
        return self._timeEnd

    @property
    def thumbnail(self):
        return self._thumbnail

    @property
    def visibility(self):
        return self._visibility

    @property
    def clipName(self):
        return self._clipName

    @timeStart.setter
    def timeStart(self, time: QTime):
        self._timeStart = time

    @timeEnd.setter
    def timeEnd(self, time: QTime):
        self._timeEnd = time

    @thumbnail.setter
    def thumbnail(self, thumb: QPixmap):
        self._thumbnail = thumb

    @visibility.setter
    def visibility(self, value: bool):
        self._visibility = value

    @clipName.setter
    def clipName(self, name: str):
        self._clipName = name
