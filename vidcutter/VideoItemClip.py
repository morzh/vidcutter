from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTime


class VideoItemClip:
    def __init__(self, *args):
        if not len(args):
            self._timeStart = QTime()
            self._timeEnd = QTime()
            self._thumbnail = QPixmap()
            self._name = ''
            self._visibility = 2
            self._description = ''

        if len(args) == 5:
            self._timeStart = args[0]
            self._timeEnd = args[1]
            self._thumbnail = args[2]
            self._name = args[3]
            self._visibility = args[4]
            self._description = ''

        self._clipClass = 'squat'  # for future challenges

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

    def print(self):
        print('\t',  'name:',  self._name, 'start time', self._timeStart, ' time end:',
              self._timeEnd, ' visibility:',  self._visibility, ' description:',  self._description)

