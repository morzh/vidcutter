from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTime
from vidcutter.data_structures.qpixmap_pickle import QPixmapPickle
from vidcutter.data_structures.video_clip_timestamps import VideoClipTimestamps
from vidcutter.data_structures.bounding_box import BoundingBox


class VideoItemClip:
    def __init__(self, *args):
        if not len(args):
            self._timeStart = QTime()
            self._timeEnd = QTime()
            self._thumbnail = QPixmapPickle()
            self._visibility = 2
        elif len(args) == 5:
            self._timeStart = args[0]
            self._timeEnd = args[1]
            self._thumbnail = args[2]
            self._name = args[3]
            self._visibility = args[4]

        self._description = ''
        self.actionClassIndex = -1
        self.boundingBox = BoundingBox()
        self.clip_timestamps: list[VideoClipTimestamps] = []

    def __str__(self):
        clip_string = f'Start time, {self._timeStart},  time end:, {self._timeEnd}, visibility:  {self._visibility}, description:  {self._description} \n'
        clip_timestamps_string = 'Clip timestamps: '
        for clip in self.clip_timestamps:
            clip_timestamps_string += f'{clip.timestamp}, '
        return clip_string + clip_timestamps_string

    def __lt__(self, other):
        return self.timeStart < other.timeStart

    def __le__(self, other):
        return self.timeStart <= other.timeStart

    def __gt__(self, other):
        return self.timeStart > other.timeStart

    def __ge__(self, other):
        return self.timeStart >= other.timeStart


    def cleanTimestamps(self):
        clip_duration = self._timeEnd.msecsSinceStartOfDay() - self._timeStart.msecsSinceStartOfDay()
        for index in reversed(range(len(self.clip_timestamps))):
            current_milliseconds = self.clip_timestamps[index].timestamp.msecsSinceStartOfDay()
            if current_milliseconds > clip_duration or current_milliseconds == 0:
                del self.clip_timestamps[index]


    def timepointsSeconds(self) -> list[float]:
        timepoints = [float] * (len(self.clip_timestamps) + 2)
        startTiemstamp = self._timeStart.msecsSinceStartOfDay() * 1e-3

        timepoints[0] = startTiemstamp
        for index, timestamp in enumerate(self.clip_timestamps):
            timepoints[index + 1] = timestamp.seconds + startTiemstamp
        timepoints[-1] = self._timeEnd.msecsSinceStartOfDay() * 1e-3

        return timepoints


    @property
    def timeStart(self) -> QTime:
        return self._timeStart

    @property
    def timeEnd(self) -> QTime:
        return self._timeEnd

    @property
    def thumbnail(self) -> QPixmapPickle:
        return self._thumbnail

    @property
    def visibility(self) -> int:
        return self._visibility

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @timeStart.setter
    def timeStart(self, time: QTime):
        self._timeStart = time

    @timeEnd.setter
    def timeEnd(self, timeEnd: QTime):
        if not timeEnd.isNull() and timeEnd.__lt__(self._timeStart):
            self._timeEnd = self._timeStart
            self._timeStart = timeEnd
        else:
            self._timeEnd = timeEnd

    @thumbnail.setter
    def thumbnail(self, thumb: QPixmap):
        self._thumbnail = thumb

    @visibility.setter
    def visibility(self, value: int):
        self._visibility = value

    @name.setter
    def name(self, name: str):
        self._name = name

    @description.setter
    def description(self, description: str):
        self._description = description
