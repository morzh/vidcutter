import pickle
import os
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QPixmap
from vidcutter.VideoItem import VideoItem
from sortedcontainers import SortedList


class VideoList:
    def __init__(self, video_issues):
        self._description: str = ''
        self._currentVideoIndex: int = 0
        self.videos: list[VideoItem] = []
        self._videoIssuesClasses = video_issues

    def __str__(self):
        print('description:', self._description)
        print('video issues classes:', self._videoIssuesClasses)
        print('videos:')
        print('-' * 50)
        for video in self.videos:
            print(video)
            print('-' * 50)

    def currentVideoClipTimeStart(self, clip_index: int) -> QTime:
        return self.videos[self._currentVideoIndex].clips[clip_index].timeStart

    @staticmethod
    def clamp(x, minimum, maximum):
        return max(minimum, min(x, maximum))

    @property
    def video_issues_classes(self) -> list:
        return self._videoIssuesClasses

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, description: str) -> None:
        if isinstance(description, str):
            self._description = description

    @property
    def current_video_index(self) -> int:
        return self._currentVideoIndex

    @current_video_index.setter
    def current_video_index(self, index: int) -> None:
        self._currentVideoIndex = index

    def setCurrentVideoIndex(self, index: int) -> None:
        self._currentVideoIndex = index

    def currentVideoFilepath(self, folder_path: str):
        return os.path.join(folder_path, self.videos[self._currentVideoIndex].filename)

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
