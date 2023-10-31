from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTime
import numpy as np


class BoundingBox:
    """
    Image bounding box in normalized coordinates
    """
    def __init__(self):
        self._x = 0.0
        self._y = 0.0
        self._width = 1.0
        self._height = 1.0
        self._confidence = 1.0

    @staticmethod
    def clamp_(self, value, minimum, maximum):
        if value < minimum:
            return minimum
        elif value > maximum:
            return maximum
        else:
            return value

    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, value) -> None:
        self._x = self.clamp_(value, 0, 1)

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, value) -> None:
        self._y = self.clamp_(value, 0, 1)

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, value) -> None:
        self._width = self.clamp_(value, 0, 1)

    @property
    def height(self) -> float:
        return self._height

    @height.setter
    def height(self, value) -> None:
        self._height = self.clamp_(value, 0, 1)

    @property
    def confidence(self) -> float:
        return self._confidence

    @confidence.setter
    def confidence(self, value) -> None:
        self._confidence = self.clamp_(value, 0, 1)


class VideoItemClip:
    def __init__(self, *args):
        if not len(args):
            self._timeStart = QTime()
            self._timeEnd = QTime()
            self._thumbnail = QPixmap()
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

    def __str__(self):
        return f'name:  {self._name}, start time, {self._timeStart},  time end:, {self._timeEnd}, visibility:  {self._visibility}, description:  {self._description} \n'

    def __lt__(self, other):
        return self.timeStart < other.timeStart

    def __le__(self, other):
        return self.timeStart <= other.timeStart

    def __gt__(self, other):
        return self.timeStart > other.timeStart

    def __ge__(self, other):
        return self.timeStart >= other.timeStart

    @property
    def timeStart(self) -> QTime:
        return self._timeStart

    @property
    def timeEnd(self) -> QTime:
        return self._timeEnd

    @property
    def thumbnail(self) -> QPixmap:
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
