# from operator import itemgetter
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTime
from vidcutter.VideoItemClip import VideoItemClip

class VideoItem:
    def __init__(self, *args):
        if not len(args):
            self._thumbnail = QPixmap()
            self._duration = QTime()
            self._filename = ''
            self.description = ''
            self.youtube_id = ''
            self.issues = []
            self.clips = []
            self._currentCLipIndex = 0
        elif len(args) == 2:
            self.thumb = args[0]
            self.filename = args[1]

    def print(self):
        print('filename:', self._filename)
        print('description:', self.description)
        print('youtube id:', self.youtube_id)
        # print('issues classes:', itemgetter(*self.issues)(a))
        print('issues classes:', self.issues)
        print('clips:')
        # print('-' * 30)
        for clip in self.clips:
            clip.print()
            # print('-' * 30)

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
    def filename(self, fp: str):
        self._filename = fp

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
