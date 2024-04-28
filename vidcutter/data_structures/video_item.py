# from operator import itemgetter

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTime
from sortedcontainers import SortedList

from vidcutter.data_structures.video_item_clip import VideoItemClip
from vidcutter.data_structures.qpixmap_pickle import QPixmapPickle


class VideoItem:
    def __init__(self):
        self._thumbnail = QPixmapPickle()
        self._duration = QTime()
        self._currentCLipIndex = 0
        self._filename = ''
        self.description = ''
        self.youtubeId = ''
        self.issues: list[str] = []
        self.clips: SortedList[VideoItemClip] = SortedList()

    def __str__(self):
        return_string = f'filename:  {self._filename} \n  description: {self.description} \n youtube id: {self.youtubeId} \n issues classes: {self.issues} \n clips:\n'
        for clip in self.clips:
            return_string += str(clip)

        return return_string

    def __getitem__(self, item):
        if len(self.clips):
            return self.clips[item]
        else:
            raise IndexError

    def __len__(self):
        return len(self.clips)

    def clipsLast(self):
        if len(self.clips):
            return self.clips[-1]
        else:
            raise Exception

    def clipsLength(self):
        return len(self.clips)

    @property
    def filename(self) -> str:
        return self._filename

    @filename.setter
    def filename(self, filename: str):
        self._filename = filename

    @property
    def thumbnail(self) -> QPixmap:
        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, thumb: QPixmap):
        self._thumbnail = thumb

    @property
    def currentClipIndex(self) -> int:
        return self._currentCLipIndex

    @currentClipIndex.setter
    def currentClipIndex(self, index: int):
        if index < 0:
            index *= -1
        self._currentCLipIndex = index

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, time: QTime):
        self._duration = time
