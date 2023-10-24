# from operator import itemgetter
from typing import List

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTime
from vidcutter.VideoItemClip import VideoItemClip
from sortedcontainers import SortedList

class VideoItem:
    def __init__(self, *args):
        if not len(args):
            self._thumbnail = QPixmap()
            self._duration = QTime()
            self._filename: str = ''
            self.description = ''
            self.youtubeId = ''
            self.issues = []
            self.clips: SortedList[VideoItemClip] = SortedList()
            self._currentCLipIndex = 0
        elif len(args) == 2:
            self.thumb = args[0]
            self.filename = args[1]

    def __str__(self):
        print('filename:', self._filename)
        print('description:', self.description)
        print('youtube id:', self.youtubeId)
        # print('issues classes:', itemgetter(*self.issues)(a))
        print('issues classes:', self.issues)
        print('clips:')
        for clip in self.clips:
            print(clip)

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
