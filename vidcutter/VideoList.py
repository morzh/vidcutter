import pickle
import os
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QPixmap
from vidcutter.VideoItem import VideoItem


class VideoList:
    def __init__(self, video_issues):
        self._description: str = ''
        self._current_video_index: int = 0
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
        return self.videos[self._current_video_index].clips[clip_index].timeStart

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
    def current_video_index(self):
        return self._current_video_index

    @current_video_index.setter
    def current_video_index(self, index: int) -> None:
        if index < 0:
            index *= -1
        self._current_video_index = index

    def setCurrentVideoIndex(self, index: int) -> None:
        if index < 0:
            index *= -1
        self._current_video_index = index

    def currentVideoFilepath(self, folder_path: str):
        return os.path.join(folder_path, self.videos[self._current_video_index].filename)

    def setCurrentVideoClipIndex(self, index):
        if len(self.videos):
            self.videos[self._current_video_index].currentClipIndex = index

    def setCurrentVideoClipStartTime(self, time: QTime):
        currentClipIndex = self.videos[self._current_video_index].currentClipIndex
        self.videos[self._current_video_index].clips[currentClipIndex].timeStart = time

    def setCurrentVideoClipEndTime(self, time: QTime):
        currentClipIndex = self.videos[self._current_video_index].currentClipIndex
        self.videos[self._current_video_index].clips[currentClipIndex].timeEnd = time

    def setCurrentVideoClipThumbnail(self, thumbnail: QPixmap):
        currentClipIndex = self.videos[self._current_video_index].currentClipIndex
        self.videos[self._current_video_index].clips[currentClipIndex].thumbnail = thumbnail

    def setCurrentVideoClipName(self, name: str):
        currentClipIndex = self.videos[self._current_video_index].currentClipIndex
        self.videos[self._current_video_index].clips[currentClipIndex].name = name

    def setCurrentVideoClipDescription(self, description: str):
        currentClipIndex = self.videos[self._current_video_index].currentClipIndex
        self.videos[self._current_video_index].clips[currentClipIndex].description = description

    def setCurrentVideoClipVisibility(self, visibility: int):
        visibility = VideoList.clamp(visibility, 0, 2)
        currentClipIndex = self.videos[self._current_video_index].currentClipIndex
        self.videos[self._current_video_index].clips[currentClipIndex].visibility = visibility
