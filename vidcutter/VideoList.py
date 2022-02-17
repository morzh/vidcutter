import pickle
import os
from PyQt5.QtCore import (QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize, Qt, QTextStream, QTime)
from PyQt5.QtGui import QPixmap
from vidcutter.VideoItem import VideoItem


class VideoList:
    def __init__(self, absolute_path: str, data_filename='data.pickle', videos=[]):
        self._absolute_path = absolute_path
        self._data_filename = data_filename
        self._description = ''
        self._currentVideoIndex = 0
        self.videos = []

    @staticmethod
    def clamp(x, minimum, maximum):
        return max(minimum, min(x, maximum))

    def readData(self):
        filepath = os.path.join(self._absolute_path, self._data_filename)
        with open(filepath, 'rb') as f:
            self.videos = pickle.load(f)

    def saveData(self):
        pickle.dump(self.videos, os.path.join(self._absolute_path, self._data_filename))

    @property
    def currentVideoIndex(self):
        return self._currentVideoIndex

    def currentVideoFilepath(self):
        return os.path.join(self._absolute_path, self.videos[self._currentVideoIndex].filename)

    def setCurrentVideoIndex(self, index: int) -> None:
        if index < 0:
            index *= -1
        self._currentVideoIndex = index

    def setCurrentClipIndex(self, index):
        if len(self.videos):
            self.videos[self._currentVideoIndex].currentClipIndex = index

    def setCurrentVideoClipStartTime(self, time: QTime):
        currentClipIndex = self.videos[self._currentVideoIndex].currentCLipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].timeStart = time

    def setCurrentVideoClipEndTime(self, time: QTime):
        currentClipIndex = self.videos[self._currentVideoIndex].currentCLipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].timeEnd = time

    def setCurrentVideoClipThumbnail(self, thumbnail: QPixmap):
        currentClipIndex = self.videos[self._currentVideoIndex].currentCLipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].thumbnail = thumbnail

    def setCurrentVideoClipName(self, name: str):
        currentClipIndex = self.videos[self._currentVideoIndex].currentCLipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].namw = name

    def setCurrentVideoClipDescription(self, description: str):
        currentClipIndex = self.videos[self._currentVideoIndex].currentCLipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].description = description

    def setCurrentVideoClipVisibility(self, visibility: int):
        visibility = VideoList.clamp(visibility, 0, 2)
        currentClipIndex = self.videos[self._currentVideoIndex].currentCLipIndex
        self.videos[self._currentVideoIndex].clips[currentClipIndex].visibility = visibility
