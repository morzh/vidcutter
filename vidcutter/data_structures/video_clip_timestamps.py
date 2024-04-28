from enum import Enum
from PyQt5.QtCore import QTime


class VideoClipTimestamps:
    class TimestampType(Enum):
        LEFT = 1
        RIGHT = 2
        DOUBLE_SIDED = 3

    def __init__(self, timestamp: QTime, timestamp_type: TimestampType):
        self.timestamp_ = timestamp
        self.timestamp_type_ = timestamp_type

    @property
    def timestamp(self):
        return self.timestamp_

    @timestamp.setter
    def timestamp(self, timestamp: QTime):
        self.timestamp_ = timestamp

    @property
    def timestamp_type(self):
        return  self.timestamp_type_

    @timestamp_type.setter
    def timestamp_type(self, timestamp_type: TimestampType):
        self.timestamp_type_ = timestamp_type
