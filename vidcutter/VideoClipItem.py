from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize,
                          Qt, QTextStream, QTime, QTimer, QUrl)

class VideoClipItem:
    def __init__(self, *args):
        if not len(args):
            self._timeStart = QTime()
            self._timeEnd = QTime()
            self._thumbnail = QPixmap()
            self._name = ''
            self._visibility = 2

        if len(args) == 5:
            self._timeStart = args[0]
            self._timeEnd = args[1]
            self._thumbnail = args[2]
            self._name = args[3]
            self._visibility = args[4]

        self._clipClass = 'squat'  # for future challenges

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
        return self._name

    @timeStart.setter
    def timeStart(self, time: QTime):
        self._timeStart = time

    @timeEnd.setter
    def timeEnd(self, timeEnd: QTime):
        if timeEnd.__lt__(self._timeStart):
            self._timeEnd = self._timeStart
            self._timeStart = timeEnd
        else:
            self._timeEnd = timeEnd

    @thumbnail.setter
    def thumbnail(self, thumb: QPixmap):
        self._thumbnail = thumb

    @visibility.setter
    def visibility(self, value: bool):
        self._visibility = value

    @clipName.setter
    def clipName(self, name: str):
        self._name = name
