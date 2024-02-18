#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from base64 import b64encode

import sys
from copy import copy
from enum import Enum

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QScrollArea

from vidcutter.VideoItemClip import VideoItemClip
from vidcutter.VideoList import VideoList

from vidcutter.widgets.timeline_widget import TimeLine


class ScalableTimeLine(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.restrictValue = 0
        self.factor_ = 1
        self.maximumFactor_ = 20
        self.baseWidth_ = 800
        self.theme = 'dark'

        self.timeline = TimeLine(self)
        self.setWidget(self.timeline)
        self.setAlignment(Qt.AlignVCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setObjectName('scalable_timeline')
        self._cutStarted = False
        self._handleHover = False

    def initAttributes(self) -> None:
        self.setEnabled(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.timeline.setEnabled(False)

    @property
    def baseWidth(self) -> int:
        return self.baseWidth_

    @baseWidth.setter
    def baseWidth(self, value: int) -> None:
        if value >= 1:
            self.baseWidth_ = value

    @property
    def factor(self) -> int:
        return self.factor_

    @factor.setter
    def factor(self, value: int) -> None:
        self.factor_ = TimeLine.clip(value, 1, self.maximumFactor_)
        self.timeline.setFixedWidth(self.factor_ * self.baseWidth_ - 2)
        self.timeline.updateClips()
        # self.repaint()

    @property
    def maximumFactor(self) -> int:
        return self.maximumFactor_

    @maximumFactor.setter
    def maximumFactor(self, value: int) -> None:
        if value >= 1:
            self.maximumFactor_ = value

    def value(self) -> float:
        return self.timeline.pointerSecondsPosition

    def setDuration(self, duration: float) -> None:
        self.timeline.duration = duration

    def setValue(self, seconds: str | float) -> None:
        try:
            seconds = float(seconds)
            self.timeline.setPositionFromSeconds(seconds)
            self.timeline.repaint()
        except ValueError('seconds should be in the float number format'):
            return

    def setEnabled(self, flag: bool) -> None:
        self.timeline.setEnabled(flag)
        super().setEnabled(flag)

    def setDisabled(self, flag: bool) -> None:
        self.timeline.setDisabled(flag)
        super().setEnabled(flag)

    def setRestrictValue(self, value, force=False) -> None:
        self.restrictValue = value

    def setClipCutStart(self, flag: float) -> None:
        self.timeline.setClipCutStart(flag)

    def update(self) -> None:
        self.timeline.update()
        super().update()

    def repaint(self):
        self.timeline.repaint()
        super().repaint()

    def renderVideoClips(self, clips: list[VideoItemClip]) -> None:
        self.timeline.clearClips()
        for videoClip in clips:
            clipStart = videoClip.timeStart.msecsSinceStartOfDay()
            clipEnd = videoClip.timeEnd.msecsSinceStartOfDay()
            clipVisibility = videoClip.visibility
            self.addClip(clipStart * 1e-3, clipEnd * 1e-3, clipVisibility)
        self.update()

    def setClipVisibility(self, index: int, state) -> None:
        self.timeline.setClipVisibility(index, state)

    def addClip(self, start: float, end: float, visibility=2) -> None:
        self.timeline.addClip(start, end, visibility)

    def switchRegions(self, index1: int, index2: int) -> None:
        region = self.timeline.clipsRectangles_.pop(index1)
        regionVisibility = self.timeline.clipsVisibility_.pop(index1)
        self.timeline.clipsRectangles_.insert(index2, region)
        self.timeline.clipsVisibility_.insert(index2, regionVisibility)
        self.update()

    def selectRegion(self, clipIndex: int) -> None:
        self.timeline.regionSelected_ = clipIndex
        self.update()

    def clearRegions(self) -> None:
        self.timeline.clearClips()

    def updateProgress(self, region: int = None) -> None:
        pass

    def clearProgress(self):
        pass

    def minimum(self):
        """minimum slider pixel position in PIXELS"""
        return self.timeline.sliderAreaHorizontalOffset

    def maximum(self):
        """maximum slider pixel position in PIXELS"""
        return self.timeline.width() - self.timeline.sliderAreaHorizontalOffset

    def width(self) -> int:
        return self.width()

    def setFixedWidth(self, width) -> None:
        super().setFixedWidth(width)
        self.baseWidth_ = width
        self.timeline.setFixedWidth(self.factor_ * self.baseWidth_ - 2)

    def setFixedHeight(self, height) -> None:
        super().setFixedHeight(height)
        self.timeline.setFixedHeight(height - 16)

    def sliderPositionFromValue(self, minimum: int, maximum: int, logicalValue: int, span: int) -> int:
        return int(float(logicalValue) / float(maximum - minimum) * span)

    def setRestrictValue(self, value: int = 0, force: bool = False) -> None:
        self.restrictValue = value
        if value > 0 or force:
            self._cutStarted = True
            self._handleHover = True
        else:
            self._cutStarted = False
            self._handleHover = False
        # self.initStyle()

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.timeline.wheelEvent(event)

    # def keyPressEvent(self, a0):
    #     self.parent.keyPressEvent(a0)
