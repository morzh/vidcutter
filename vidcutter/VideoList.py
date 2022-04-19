import pickle
import os
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QPixmap
from vidcutter.VideoItem import VideoItem


class VideoList:
    def __init__(self, videoIssues: list):
        self._description = ''
        self._currentVideoIndex = 0
        self.videos = []
        self._videoIssuesClasses = videoIssues

    def print(self):
        print('description:', self._description)
        print('video issues classes:', self._videoIssuesClasses)
        print('videos:')
        print('-' * 50)
        for video in self.videos:
            video.print()
            print('-' * 50)

    def currentVideoClipTimeStart(self) -> QTime:
        return self.parent.videoList.videos[self.parent.videoList.currentVideoIndex].clips[self.current_rectangle_index].timeStart

    @staticmethod
    def clamp(x, minimum, maximum):
        return max(minimum, min(x, maximum))
    '''
    def readData(self):
        filepath = os.path.join(self._absolutePath, self._data_filename)
        with open(filepath, 'rb') as f:
            self.videos = pickle.load(f)

    def saveData(self):
        data_filepath_temporary = os.path.join(self._absolutePath, self._data_temporary_filename)
        data_filepath = os.path.join(self._absolutePath, self._data_filename)
        try:
            with open(data_filepath_temporary, 'wb') as f:
                pickle.dump(self.videos, f)
            os.rename(data_filepath_temporary, data_filepath)
        except OSError:
            print('project save failed')

    def saveDataQtThread(self):
        pass
    '''
    @property
    def videoIssuesClasses(self):
        return self._videoIssuesClasses

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, description: str) -> None:
        if isinstance(description, str):
            self._description = description

    @property
    def videoIssues(self) -> list:
        return self._video_issues

    @videoIssues.setter
    def videoIssues(self, issues: list) -> None:
        if isinstance(issues, list):
            self._video_issues = issues

    @property
    def absolutePath(self) -> str:
        return self._absolutePath

    @absolutePath.setter
    def absolutePath(self, path: str) -> None:
        self._absolutePath = path

    @property
    def currentVideoIndex(self):
        return self._currentVideoIndex

    @currentVideoIndex.setter
    def currentVideoIndex(self, index: int) -> None:
        if index < 0:
            index *= -1
        self._currentVideoIndex = index

    def setCurrentVideoIndex(self, index: int) -> None:
        if index < 0:
            index *= -1
        self._currentVideoIndex = index

    def currentVideoFilepath(self, folderPath: str):
        return os.path.join(folderPath, self.videos[self._currentVideoIndex].filename)

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
