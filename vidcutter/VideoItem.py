from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize, Qt, QTextStream, QTime, QTimer, QUrl)
from vidcutter.VideoClipItem import VideoClipItem

class VideoItem:
    def __init__(self, *args):
        if not len(args):
            self._thumbnail = QPixmap()
            self._filepath = ''
            self.description = ''
            self.clips = []
        elif len(args) == 2:
            self.thumb = args[0]
            self.filepath = args[1]

    def clipsAppend(self, clipItem: VideoClipItem):
        self.clips.append(clipItem)

    def clipsPop(self):
        self.clips.pop()

    def clipsLast(self):
        if len(self.clips):
            return self.clips[-1]
        else:
            raise Exception

    def clipsClear(self):
        self.clips.clear()

    def clipsLength(self):
        return len(self.clips)

    @property
    def filepath(self):
        return self._filepath

    @property
    def thumbnail(self):
        return self._thumbnail

    @filepath.setter
    def filepath(self, fp: str):
        self._filepath = fp

    @thumbnail.setter
    def thumbnail(self, thumb: QPixmap):
        self._thumbnail = thumb
