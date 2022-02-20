import pickle
import os
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QPixmap
from vidcutter.VideoItem import VideoItem


class VideoList:
    def __init__(self):
        self._absolutePath = ''
        self._data_filename = 'data.pickle'
        self._description = ''
        self._currentVideoIndex = 0
        self.videos = []

    @staticmethod
    def clamp(x, minimum, maximum):
        return max(minimum, min(x, maximum))

    def readData(self):
        filepath = os.path.join(self._absolutePath, self._data_filename)
        with open(filepath, 'rb') as f:
            self.videos = pickle.load(f)

    def saveData(self):
        data_filepath = os.path.join(self._absolutePath, self._data_filename)
        # print('project files saved to', data_filepath)
        with open(data_filepath, 'wb') as f:
            pickle.dump(self.videos, f)

    @property
    def absolutePath(self) -> str:
        return self._absolutePath

    @absolutePath.setter
    def absolutePath(self, path: str) -> None:
        self._absolutePath = path

    @property
    def currentVideoIndex(self):
        return self._currentVideoIndex

    def currentVideoFilepath(self):
        return os.path.join(self._absolutePath, self.videos[self._currentVideoIndex].filename)

    def setCurrentVideoIndex(self, index: int) -> None:
        if index < 0:
            index *= -1
        self._currentVideoIndex = index

    def setCurrentVideoClipIndex(self, index):
        if len(self.videos):
            self.videos[self._currentVideoIndex].currentClipIndex = index

    def setCurrentVideoClipStartTime(self, time: QTime):
        currentClipIndex = self.videos[self._currentVideoIndex].currentClipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].timeStart = time

    def setCurrentVideoClipEndTime(self, time: QTime):
        currentClipIndex = self.videos[self._currentVideoIndex].currentClipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].timeEnd = time

    def setCurrentVideoClipThumbnail(self, thumbnail: QPixmap):
        currentClipIndex = self.videos[self._currentVideoIndex].currentClipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].thumbnail = thumbnail

    def setCurrentVideoClipName(self, name: str):
        currentClipIndex = self.videos[self._currentVideoIndex].currentClipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].name = name

    def setCurrentVideoClipDescription(self, description: str):
        currentClipIndex = self.videos[self._currentVideoIndex].currentClipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].description = description

    def setCurrentVideoClipVisibility(self, visibility: int):
        visibility = VideoList.clamp(visibility, 0, 2)
        currentClipIndex = self.videos[self._currentVideoIndex].currentClipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].visibility = visibility
