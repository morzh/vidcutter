#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from base64 import b64encode

import sys
from copy import copy
from enum import Enum

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint, QLine, QRect, QRectF, pyqtSignal, QEvent, QObject, QTime
from PyQt5.QtGui import QPainter, QMouseEvent, QColor, QFont, QBrush, QPalette, QPen, QPolygon, QPainterPath, QPixmap
from PyQt5.QtWidgets import QStyle, QStylePainter, QWidget, QStyleOptionSlider, QScrollArea, QVBoxLayout, QPushButton, QHBoxLayout, QLabel

from vidcutter.VideoItemClip import VideoItemClip
from vidcutter.VideoList import VideoList


class TimeLine(QWidget):
    sliderMoved = pyqtSignal(float)

    class CursorStates(Enum):
        cursorOnBeginSide = 1
        cursorOnEndSide = 2
        cursorIsInside = 3

    class RectangleEditState(Enum):
        freeState = 1
        buildingSquare = 2
        beginSideEdit = 3
        endSideEdit = 4
        rectangleMove = 5

    def __init__(self, parent=None):
        super().__init__()
        self.duration = -1.0
        self.length = 400
        self.parent = parent

        self.sliderAreaHorizontalOffset = 8
        self.sliderAreaTopOffset = 15
        self.sliderAreaHeight = 27
        self.sliderAreaTicksGap = 15
        self.majorTicksHeight = 20
        self.minorTicksHeight = 10
        self.timeLineHeight = 85
        self.setObjectName('timeline')

        # Set variables
        self.backgroundColor = QColor('#1b2326') if self.parent.theme == 'dark' else QColor(187, 187, 187)
        self.textColor = QColor(190, 190, 190) if self.parent.theme == 'dark' else Qt.black
        self.font = QFont('Decorative', 10)
        self.pos = None
        self.pointerPixelPosition = None
        self.pointerTimePosition = None
        self.selectedSample = None
        self.clicking = False  # Check if mouse left button is being pressed
        self.is_in = False  # check if user is in the widget
        self.setObjectName('timeline')
        # self.parent.mpvWidget.positionChanged.connect(self.positionChanged)

        self.setMouseTracking(True)  # Mouse events
        self.setAutoFillBackground(True)  # background
        self.initAttributes()

        self.currentRectangleIndex = -1
        self.freeCursorOnSide = 0
        self.state = self.RectangleEditState.freeState
        self.begin = QPoint()
        self.end = QPoint()
        self.numberGradientSteps = 50
        self.regionOutlineWidth = 4
        self.videoListRef = None

        self.progressbars_ = []
        self.clipsRectangles_ = []
        self.clipsVisibility_ = []
        self.regionSelected_ = -1
        self.regionHeight_ = 20


    def initAttributes(self):
        self.setFixedWidth(self.length)
        self.setFixedHeight(self.timeLineHeight)
        # Set Background
        palette = QPalette()
        palette.setColor(QPalette.Background, self.backgroundColor)
        self.setPalette(palette)

    def _drawTicks(self, painter: QStylePainter):
        scale = self.getScale()
        y = self.rect().top() + self.sliderAreaTopOffset + self.sliderAreaHeight + 8
        tickStep = 20
        timeTickStep = tickStep * 5
        tickColor = QColor('#8F8F8F' if self.parent.theme == 'dark' else '#444')
        millisecondsFlag = True if self.getTimeString(0) == self.getTimeString(timeTickStep * scale) else False

        for i in range(0, self.width() - 2 * self.sliderAreaHorizontalOffset, tickStep):
            x = i + self.sliderAreaHorizontalOffset
            if i % timeTickStep == 0:
                h, w, z = 30, 1, 10
                if i < self.width() - (tickStep * 5):
                    painter.setPen(self.textColor)
                    timecode = self.getTimeString(i * scale, millisecondsFlag)
                    painter.drawText(x + 5, y + 25, timecode)
            else:
                h, w, z = 8, 1, 10

            pen = QPen(tickColor)  # , Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            pen.setWidthF(w)
            painter.setPen(pen)
            painter.drawLine(x, y, x, y + h)

    def _drawSlider(self, painter):
        # print('self.pointerPixelPosition', self.pointerPixelPosition)
        if self.pos is not None and self.is_in:
            x = self.clip(self.pos.x(), self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            painter.drawLine(x, self.sliderAreaTopOffset, x, self.timeLineHeight)
            # print('drawSlider_::self.pos.x()', self.pos.x(), x)
        if self.pointerPixelPosition is not None:
            x = int(self.pointerPixelPosition)
            y = self.sliderAreaTopOffset - 1
            line = QLine(QPoint(x, self.sliderAreaTopOffset), QPoint(x, self.height()))
            sliderHandle = QPolygon([QPoint(x - 7, 5), QPoint(x + 7, 5), QPoint(x, y)])
        else:
            x = self.sliderAreaHorizontalOffset
            y = self.sliderAreaTopOffset - 1
            line = QLine(QPoint(x, 0), QPoint(x, self.height()))
            sliderHandle = QPolygon([QPoint(x - 7, 5), QPoint(x + 7, 5), QPoint(x, y)])

        painter.setPen(Qt.darkCyan)
        painter.setBrush(QBrush(Qt.darkCyan))
        painter.drawPolygon(sliderHandle)
        painter.drawLine(line)

    def _drawFrame(self, painter):
        if self.isEnabled():
            painter.setPen(self.textColor)
        else:
            painter.setPen(QColor(60, 60, 60))

        painter.drawRoundedRect(self.sliderAreaHorizontalOffset, self.sliderAreaTopOffset,
                                self.width() - 2 * self.sliderAreaHorizontalOffset, self.sliderAreaHeight,
                                3, 3)

    def _drawClips(self, painter: QStylePainter, opt: QStyleOptionSlider):
        # opt = QStyleOptionSlider()
        # opt.subControls = QStyle.SC_CustomBase
        # painter.drawComplexControl(QStyle.CC_Slider, opt)
        videoIndex = self.videoListRef.currentVideoIndex
        if not len(self.progressbars_):
            if len(self.clipsRectangles_) == len(self.clipsVisibility_):  # should always be true
                visible_region = self.visibleRegion().boundingRect()
                for index, (clipRectangle, clipVisibility) in enumerate(zip(self.clipsRectangles_, self.clipsVisibility_)):
                    if clipVisibility == 0:
                        continue
                    clipRectangle.setY(int((self.height() - self.regionHeight_) / 2) - 13)
                    clipRectangle.setHeight(self.regionHeight_)
                    rectClass = clipRectangle.adjusted(0, 0, 0, 0)
                    brushColor = QColor(150, 190, 78, 150) if self.clipsRectangles_.index(clipRectangle) == self.regionSelected_ else QColor(237, 242, 255, 150)
                    painter.setBrush(brushColor)
                    painter.setPen(QColor(50, 50, 50, 170))
                    painter.setRenderHints(QPainter.HighQualityAntialiasing)
                    painter.drawRoundedRect(clipRectangle, 2, 2)
                    painter.setFont(QFont('Noto Sans', 13 if sys.platform == 'darwin' else 11, QFont.SansSerif))
                    painter.setPen(Qt.black if self.parent.theme == 'dark' else Qt.white)
                    rectClass = rectClass.intersected(visible_region)
                    rectClass = rectClass.adjusted(5, 0, -5, 0)
                    actionClassIndex = self.videoListRef[videoIndex].clips[index].actionClassIndex
                    if actionClassIndex == -1:
                        actionClassLabel = copy(self.parent.videoList.actionClassUnknownLabel)
                    else:
                        actionClassLabel = copy(self.videoListRef.actionClassesLabels[actionClassIndex])
                    painter.drawText(rectClass, Qt.AlignBottom | Qt.AlignLeft, actionClassLabel)
        # opt.activeSubControls = opt.subControls = QStyle.SC_SliderHandle
        # painter.drawComplexControl(QStyle.CC_Slider, opt)

    def _drawCLipsEditMode_(self, painter: QStylePainter):
        glowAlpha = 150
        highlightColor = QColor(190, 85, 200, 255)
        glowColor = QColor(255, 255, 255, glowAlpha)
        maximumGradientSteps = copy(self.clipsRectangles_[self.currentRectangleIndex].width())
        maximumGradientSteps = int(maximumGradientSteps)
        numberGradientSteps = min(self.numberGradientSteps, maximumGradientSteps)

        if self.freeCursorOnSide == self.CursorStates.cursorOnBeginSide:
            begin = copy(self.clipsRectangles_[self.currentRectangleIndex].topLeft())
            end = copy(self.clipsRectangles_[self.currentRectangleIndex].bottomLeft())
            coordinateX = begin.x()
            begin.setX(coordinateX + self.regionOutlineWidth)
            end.setX(coordinateX + self.regionOutlineWidth)
            step = int(glowAlpha / numberGradientSteps)
            for index_step in range(numberGradientSteps):
                begin.setX(coordinateX + index_step)
                end.setX(coordinateX + index_step)
                glowColor.setAlpha(glowAlpha - step * index_step)
                painter.setPen(QPen(glowColor, 1, Qt.SolidLine))
                painter.drawLine(begin, end)

            begin = self.clipsRectangles_[self.currentRectangleIndex].topLeft()
            end = self.clipsRectangles_[self.currentRectangleIndex].bottomLeft()
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            painter.drawLine(begin, end)

        elif self.freeCursorOnSide == self.CursorStates.cursorOnEndSide:
            begin = copy(self.clipsRectangles_[self.currentRectangleIndex].topRight())
            end = copy(self.clipsRectangles_[self.currentRectangleIndex].bottomRight())
            coordinateX = end.x()
            begin.setX(coordinateX - self.regionOutlineWidth)
            end.setX(coordinateX - self.regionOutlineWidth)
            step = int(glowAlpha / numberGradientSteps)
            for index_step in range(numberGradientSteps):
                begin.setX(coordinateX - index_step)
                end.setX(coordinateX - index_step)
                glowColor.setAlpha(glowAlpha - step * index_step)
                painter.setPen(QPen(glowColor, 1, Qt.SolidLine))
                painter.drawLine(begin, end)

            begin = self.clipsRectangles_[self.currentRectangleIndex].topRight()
            end = self.clipsRectangles_[self.currentRectangleIndex].bottomRight()
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            painter.drawLine(begin, end)
        elif self.freeCursorOnSide == self.CursorStates.cursorIsInside:
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            brushColor = QColor(237, 242, 255, 150)
            painter.setBrush(brushColor)
            painter.setRenderHints(QPainter.HighQualityAntialiasing)
            painter.drawRoundedRect(self.clipsRectangles_[self.currentRectangleIndex], 2, 2)

    def paintEvent(self, event):
        opt = QStyleOptionSlider()
        painter = QPainter()
        painter.begin(self)
        # painter.setRenderHint(QPainter.Antialiasing)
        self._drawFrame(painter)
        if self.isEnabled():
            painter.setFont(self.font)
            self._drawTicks(painter)
            self._drawSlider(painter)
            self._drawClips(painter, opt)
            if not self.freeCursorOnSide:
                return
            self._drawCLipsEditMode_(painter)

        painter.end()

    def setRegionVizivility(self, index, state):
        if len(self._regionsVisibility) > 0:
            self._regionsVisibility[index] = state
            self.update()

    # Mouse movement
    def _pixelsToSeconds(self, pixelPosition: int) -> float:
        return (pixelPosition - self.sliderAreaHorizontalOffset) * self.getScale()

    def _pixelsToQTime(self, pixels: int) -> QTime:
        seconds = self._pixelsToSeconds(pixels)

        milliseconds = int(round(1e3 * (seconds - int(seconds))))
        seconds = int(seconds)
        minutes = int(seconds / 60)
        hours = int(minutes / 60)
        time = QTime(hours, minutes, seconds, milliseconds)
        return time
    # Mouse pressed

    def _secondsToPixelPosition(self, seconds: float) -> int:
        return round(seconds / self.getScale() + self.sliderAreaHorizontalOffset)

    def setPositionFromQTime(self):
        pass

    def setPositionFromSeconds(self, seconds: float) -> None:
        self.pointerPixelPosition = self._secondsToPixelPosition(seconds)
        self.pointerTimePosition = seconds
        # self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        self.pos = event.pos()
        x = event.pos().x()
        # if mouse is being pressed, update pointer
        if self.clicking and x:
            self.pointerPixelPosition = self.clip(x, self.sliderAreaHorizontalOffset,
                                                  self.width() - self.sliderAreaHorizontalOffset)
            # self.sliderMoved.emit(self.pointerPixelPosition)
        self.update()
    # Mouse release

    def mousePressEvent(self, event: QMouseEvent):
        modifierPressed = QApplication.keyboardModifiers()

        if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier and event.button() == Qt.LeftButton:
            # event.accept()re
            self.clicking = False
        elif (modifierPressed & Qt.AltModifier) == Qt.AltModifier and event.button() == Qt.LeftButton:
            index = self.mouseCursorClipIndex(event.pos())
            if index != -1:
                clip = self.videoListRef.videos[self.videoListRef.currentVideoIndex].clips[index]
                clipStartSeconds = 1e-3 * clip.timeStart.msecsSinceStartOfDay()
                self.setPositionFromSeconds(clipStartSeconds)
                self.parent.parent.playMediaTimeClip(index)
                self.clicking = False
                # event.accept()
        elif event.button() == Qt.LeftButton:
            self.clicking = True

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.clicking:
            x = event.pos().x()
            self.pointerPixelPosition = self.clip(x, self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            self.pointerTimePosition = self._pixelsToSeconds(self.pointerPixelPosition)
        self.sliderMoved.emit(self.pointerTimePosition)
        self.clicking = False  # Set clicking check to false
        self.update()

    def mouseCursorState(self, e_pos) -> CursorStates:
        if len(self.clipsRectangles_) > 0:
            for region_idx in range(len(self.clipsRectangles_)):
                if self.clipsVisibility_[region_idx]:
                    self.begin = self.clipsRectangles_[region_idx].topLeft()
                    self.end = self.clipsRectangles_[region_idx].bottomRight()
                    y1, y2 = sorted([self.begin.y(), self.end.y()])
                    if y1 <= e_pos.y() <= y2:
                        self.currentRectangleIndex = region_idx
                        if abs(self.begin.x() - e_pos.x()) <= 5:
                            return self.CursorStates.cursorOnBeginSide
                        elif abs(self.end.x() - e_pos.x()) <= 5:
                            return self.CursorStates.cursorOnEndSide
                        elif self.begin.x() + 5 < e_pos.x() < self.end.x() - 5:
                            return self.CursorStates.cursorIsInside
        return 0

    def mouseCursorClipIndex(self, e_pos) -> int:
        if len(self.clipsRectangles_) > 0:
            for clipIndex in range(len(self.clipsRectangles_)):
                self.begin = self.clipsRectangles_[clipIndex].topLeft()
                self.end = self.clipsRectangles_[clipIndex].bottomRight()
                y1, y2 = sorted([self.begin.y(), self.end.y()])
                if y1 <= e_pos.y() <= y2 and self.begin.x() < e_pos.x() < self.end.x():
                    return clipIndex
        return -1

    def applyEvent(self, event):
        if self.state == self.RectangleEditState.beginSideEdit:
            rectangleLeftValue = max(event.x(), 0)
            self.clipsRectangles_[self.currentRectangleIndex].setLeft(rectangleLeftValue)
            timeStart = self._pixelsToQTime(rectangleLeftValue)
            self.videoListRef.setCurrentVideoClipIndex(self.currentRectangleIndex)
            self.videoListRef.setCurrentVideoClipStartTime(timeStart)

        elif self.state == self.RectangleEditState.endSideEdit:
            rectangleRightValue = min(event.x(), self.width() - 1)
            self.clipsRectangles_[self.currentRectangleIndex].setRight(rectangleRightValue)
            timeEnd = self._pixelsToQTime(rectangleRightValue)
            self.videoListRef.setCurrentVideoClipIndex(self.currentRectangleIndex)
            self.videoListRef.setCurrentVideoClipEndTime(timeEnd)

        elif self.state == self.RectangleEditState.rectangleMove:
            delta_value = event.x() - self.dragPosition.x()
            shift_value = self.dragRectPosition.x() + delta_value
            self.clipsRectangles_[self.currentRectangleIndex].moveLeft(shift_value)

            rectangleLeftValue = max(self.clipsRectangles_[self.currentRectangleIndex].left(), 0)
            rectangleRightValue = min(self.clipsRectangles_[self.currentRectangleIndex].right(), self.width() - 1)
            timeStart = self._pixelsToQTime(rectangleLeftValue)
            timeEnd = self._pixelsToQTime(rectangleRightValue)

            self.videoListRef.setCurrentVideoClipIndex(self.currentRectangleIndex)
            self.videoListRef.setCurrentVideoClipStartTime(timeStart)
            self.videoListRef.setCurrentVideoClipEndTime(timeEnd)

    def eventFilter(self, obj: QObject, event: QMouseEvent) -> bool:
        modifierPressed = QApplication.keyboardModifiers()
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
                self.applyEvent(event)
                self.unsetCursor()
            if len(self.videoListRef.videos[self.videoListRef.currentVideoIndex].clips) == 0:
                return False

            currentVideoIndex = self.videoListRef.currentVideoIndex
            thumbnail = self.parent.parent.captureImage(self.parent.parent.currentMedia, self.videoListRef.currentVideoClipTimeStart(self.currentRectangleIndex))
            self.videoListRef.videos[currentVideoIndex].clips[self.currentRectangleIndex].thumbnail = thumbnail

            clip = self.videoListRef.videos[currentVideoIndex].clips[self.currentRectangleIndex]
            self.videoListRef.videos[currentVideoIndex].clips.pop(self.currentRectangleIndex)
            self.currentRectangleIndex = self.videoListRef.videos[currentVideoIndex].clips.bisect_right(clip)
            self.videoListRef.videos[currentVideoIndex].clips.add(clip)

            self.parent.parent.renderVideoClips()
            self.state = self.RectangleEditState.freeState
            self.freeCursorOnSide = 0
            self.repaint()

        elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
                self.dragPosition = event.pos()
                self.dragRectPosition = self.clipsRectangles_[self.currentRectangleIndex].topLeft()
                side = self.mouseCursorState(event.pos())
                if side == self.CursorStates.cursorOnBeginSide:
                    self.state = self.RectangleEditState.beginSideEdit
                elif side == self.CursorStates.cursorOnEndSide:
                    self.state = self.RectangleEditState.endSideEdit
                elif side == self.CursorStates.cursorIsInside:
                    self.state = self.RectangleEditState.rectangleMove
            elif self.parent.parent.mediaAvailable and self.isEnabled() and (modifierPressed & Qt.AltModifier) == Qt.AltModifier:
                pass
            elif self.parent.parent.mediaAvailable and self.isEnabled():
                new_position = self._pixelsToSeconds(event.x())
                # new_position = self.sliderValueFromPosition(self.minimum(), self.maximum(), event.x() - self.offset, self.width() - (self.offset * 2))
                # new_position = int(event.x() / self.width() * (self.maximum() - self.minimum()))
                # self.setValue(new_position)
                self.parent.parent.setPosition(new_position)
                self.parent.parent.parent.mousePressEvent(event)

        elif event.type() == QEvent.MouseMove and event.type() != QEvent.MouseButtonPress:
            if (int(modifierPressed) & Qt.ControlModifier) == Qt.ControlModifier:
                if self.state == self.RectangleEditState.freeState:
                    self.freeCursorOnSide = self.mouseCursorState(event.pos())
                    if self.freeCursorOnSide:
                        self.setCursor(Qt.SizeHorCursor)
                    else:
                        self.unsetCursor()
                else:
                    self.applyEvent(event)
            else:
                self.state = self.RectangleEditState.freeState
                self.freeCursorOnSide = 0
                self.unsetCursor()
            self.repaint()

        # elif event.type() == QEvent.MouseButtonPress and (modifierPressed & Qt.AltModifier) == Qt.AltModifier:
        #     self.mouseCursorClipIndex(event)

        return super().eventFilter(obj, event)

    # Enter
    def enterEvent(self, event):
        self.is_in = True

    # Leave
    def leaveEvent(self, event):
        self.is_in = False
        self.update()

    def timeToPixelPosition(self, time: float):
        pass

    @staticmethod
    def clip(value, minimum, maximum):
        return minimum if value < minimum else maximum if value > maximum else value

    def getTimeString(self, seconds, return_milliseconds=False):
        """Get time string from seconds"""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if not return_milliseconds:
            return "%02d:%02d:%02d" % (hours, minutes, seconds)
        else:
            milliseconds = int(1e3 * (seconds % 1))
            return "%02d:%02d:%02d.%03d" % (hours, minutes, seconds, milliseconds)

    # Get scale from length
    def getScale(self) -> float:
        if self.duration < 1e-6:
            return 1.0
        else:
            return float(self.duration) / float(self.width() - 2 * self.sliderAreaHorizontalOffset)

    def getDuration(self) -> float:
        return self.duration

    def getSelectedSample(self):
        return self.selectedSample

    def setBackgroundColor(self, color) -> None:
        self.backgroundColor = color

    def setTextColor(self, color) -> None:
        self.textColor = color

    def setTextFont(self, font):
        self.font = font


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

    @property
    def maximumFactor(self) -> int:
        return self.maximumFactor_

    @maximumFactor.setter
    def maximumFactor(self, value: int) -> None:
        if value >= 1:
            self.maximumFactor_ = value

    def value(self) -> float:
        return self.timeline.pointerTimePosition

    def setDuration(self, duration) -> None:
        self.timeline.duration = duration

    def setValue(self, seconds: str | float) -> None:
        try:
            seconds = float(seconds)
            self.timeline.setPositionFromSeconds(seconds)
            self.timeline.repaint()
        except ValueError('seconds should be in the float number format'):
            return

    def setEnabled(self, flag) -> None:
        self.timeline.setEnabled(flag)
        super().setEnabled(flag)

    def setRestrictValue(self, value, force=False) -> None:
        self.restrictValue = value

    def update(self) -> None:
        self.timeline.update()
        super().update()

    def renderVideoClips(self, clips: list[VideoItemClip]):
        self.timeline.clearRegions()
        for videoClip in clips:
            clipStart = videoClip.timeStart.msecsSinceStartOfDay()
            clipEnd = videoClip.timeEnd.msecsSinceStartOfDay()
            clipVisibility = videoClip.visibility
            self.addClip(clipStart.msecsSinceStartOfDay() * 1e-3, clipEnd.msecsSinceStartOfDay() * 1e-3, clipVisibility)
        self.update()

    def addClip(self, start: float, end: float, visibility=2) -> None:

        startPixelPosition = self.timeline._secondsToPixelPosition(start)
        endPixelPosition = self.timeline._secondsToPixelPosition(end)

        # startPixelPosition = self.sliderPositionFromValue(self.minimum(), self.maximum(), start - self.offset, self.width() - (self.offset * 2))
        # endPixelPosition = self.sliderPositionFromValue(self.minimum(), self.maximum(), end - self.offset, self.width() - (self.offset * 2))

        width = endPixelPosition - startPixelPosition
        y = int((self.height() - self.timeline.regionHeight_) / 2)
        height = self.timeline.regionHeight_
        self.timeline.clipsRectangles_.append(QRect(startPixelPosition, y, width, height))
        self.timeline.clipsVisibility_.append(visibility)
        self.update()

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
        self.timeline.clipsRectangles_.clear()
        self.timeline.clipsVisibility_.clear()
        self.timeline.regionSelected_ = -1
        self.update()

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

    def eventFilter(self, object: QObject, event: QEvent):
        return self.timeline.eventFilter(object, event)

