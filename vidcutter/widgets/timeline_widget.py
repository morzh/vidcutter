#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from copy import copy
from enum import Enum

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint, QLine, QRect, pyqtSignal, QTime
from PyQt5.QtGui import QPainter, QMouseEvent, QWheelEvent, QColor, QFont, QBrush, QPalette, QPen, QPolygon
from PyQt5.QtWidgets import QStylePainter, QWidget, QStyleOptionSlider

from vidcutter.data_structures.video_clip_timestamps import VideoClipTimestamps
from vidcutter.data_structures.video_item_clip import VideoItemClip


class TimeLine(QWidget):
    sliderMoved = pyqtSignal(float)

    class Clip:
        def __init__(self, rectangle: QRect, visibility: int):
            self.rectangle = rectangle
            self.visibility = visibility
            self.timestamps: list[int] = []

    class CursorStates(Enum):
        cursorIsOutside = 0
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
        self.position = None
        self.pointerPixelPosition = self.sliderAreaHorizontalOffset
        self.pointerSecondsPosition = 0.0
        self.clipCutStartPosition = 0.0
        self.selectedSample = None
        self.clicking = False  # Check if mouse left button is being pressed
        self.isIn = False  # check if user is in the widget
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
        self.numberGradientSteps: int = 50
        self.regionOutlineWidth = 4
        self.videoListRef = None

        self.progressbars_ = []
        self.clips: list[TimeLine.Clip] = []

        self.regionSelected_ = -1
        self.regionHeight_ = 20
        self.clipRectangleOffset = 6

    def initAttributes(self):
        self.setFixedWidth(self.length)
        self.setFixedHeight(self.timeLineHeight)
        # Set Background
        palette = QPalette()
        palette.setColor(QPalette.Background, self.backgroundColor)
        self.setPalette(palette)
        self.setFocusPolicy(Qt.NoFocus)

    def clearClips(self):
        self.clips.clear()
        self.regionSelected_ = -1
        self.update()

    def updateClips(self):
        self.clearClips()
        videoClipsList = self.videoListRef[self.videoListRef.currentVideoIndex].clips
        for videoClip in videoClipsList:
            self.addClip(videoClip)

    def addClip(self, videoClip: VideoItemClip) -> None:
        videoClipTimeStart = videoClip.timeStart.msecsSinceStartOfDay() * 1e-3
        videoClipTimeEnd = videoClip.timeEnd.msecsSinceStartOfDay() * 1e-3
        videoClipVisibility = videoClip.visibility

        timelineClipPixelStart = self._secondsToPixelPosition(videoClipTimeStart)
        timelineClipPixelEnd = self._secondsToPixelPosition(videoClipTimeEnd)

        timelineClipPixelWidth = timelineClipPixelEnd - timelineClipPixelStart
        y = int((self.height() - self.regionHeight_) / 2)
        timelineClipRectangle = QRect(timelineClipPixelStart, y, timelineClipPixelWidth, self.regionHeight_)

        timelineClip = TimeLine.Clip(timelineClipRectangle, videoClipVisibility)
        for timestamp in videoClip.clip_timestamps:
            currentTimestampPixelPosition = timelineClipPixelStart + self._secondsToPixelPosition(timestamp.timestamp.msecsSinceStartOfDay() * 1e-3)
            timelineClip.timestamps.append(currentTimestampPixelPosition)

        self.clips.append(timelineClip)
        self.update()

    def setClipVisibility(self, index: int, state):
        if len(self.clips):
            self.clips[index].visibility = state
            self.repaint()

    def setClipCutStart(self, seconds: float) -> None:
        self.clipCutStartPosition = seconds

    def repaint(self):
        self.pointerPixelPosition = self._secondsToPixelPosition(self.pointerSecondsPosition)
        super().repaint()

    def paintEvent(self, event):
        opt = QStyleOptionSlider()
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._drawFrame(painter)
        if self.isEnabled():
            painter.setFont(self.font)
            self._drawCutSegment(painter)
            self._drawTicks(painter)
            self._drawSlider(painter)
            self._drawVideoClips(painter, opt)
            if not self.freeCursorOnSide:
                return
            if self.currentRectangleIndex != -1 and self.parent.parent.mediaAvailable:
                self._drawCLipsEditMode_(painter)
        painter.end()

    def _drawCutSegment(self, painter):
        if self.parent.parent.inCut:
            cutStartInPixels = self._secondsToPixelPosition(self.clipCutStartPosition)
            cutEndInPixels = self.pointerPixelPosition
            cutWidthPixels = cutEndInPixels - cutStartInPixels
            painter.setPen(QColor(190, 85, 200, 150))
            painter.setBrush(QColor(190, 85, 200, 100))
            painter.drawRect(cutStartInPixels, self.sliderAreaTopOffset, cutWidthPixels, self.sliderAreaHeight)

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
        if self.position is not None and self.isIn:
            x = self.clip(self.position.x(), self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
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

    def _drawFrame(self, painter: QStylePainter) -> None:
        if self.isEnabled():
            painter.setPen(self.textColor)
        else:
            painter.setPen(QColor(60, 60, 60))

        painter.drawRoundedRect(self.sliderAreaHorizontalOffset, self.sliderAreaTopOffset,
                                self.width() - 2 * self.sliderAreaHorizontalOffset, self.sliderAreaHeight,
                                3, 3)

    def _drawVideoClips(self, painter: QStylePainter, opt: QStyleOptionSlider) -> None:
        videoIndex = self.videoListRef.currentVideoIndex
        if not len(self.progressbars_):
            visible_region = self.visibleRegion().boundingRect()
            for index, clip in enumerate(self.clips):
                currentClipAlpha = 150 if clip.visibility else 30
                currentClipRectangle = clip.rectangle
                currentClipRectangle.setY(int((self.height() - self.regionHeight_) / 2) - 2 * self.clipRectangleOffset - 1)
                currentClipRectangle.setHeight(self.regionHeight_)
                rectClass = currentClipRectangle.adjusted(0, 0, 0, 0)
                brushColor = QColor(150, 190, 78, currentClipAlpha) if index == self.regionSelected_ else QColor(237, 242, 255, currentClipAlpha)
                painter.setBrush(brushColor)
                painter.setPen(QColor(50, 50, 50, 170))
                painter.setRenderHints(QPainter.HighQualityAntialiasing)
                painter.drawRoundedRect(currentClipRectangle, 2, 2)
                painter.setFont(QFont('Noto Sans', 13 if sys.platform == 'darwin' else 11, QFont.SansSerif))
                painter.setPen(Qt.black if self.parent.theme == 'dark' else Qt.white)
                rectClass = rectClass.intersected(visible_region)
                rectClass = rectClass.adjusted(5, 0, -5, 0)
                actionClassIndex = self.videoListRef[videoIndex].clips[index].actionClassIndex
                if actionClassIndex == -1:
                    actionClassLabel = copy(self.videoListRef.actionClassUnknownLabel)
                else:
                    actionClassLabel = copy(self.videoListRef.actionClassesLabels[actionClassIndex])
                painter.drawText(rectClass, Qt.AlignBottom | Qt.AlignLeft, actionClassLabel)

                self._draw_videoClipTimestamps(clip, painter)

    def _draw_videoClipTimestamps(self, clip: Clip, painter: QStylePainter) -> None:
        penColor = QColor(50, 50, 50, 180)
        triangleHeight = 3
        triangleHalfWidth = 7
        for timestamp in clip.timestamps:
            painter.setPen(QPen(QColor(50, 50, 50, 220), 1, Qt.SolidLine))
            lineYTop = self.sliderAreaTopOffset + self.clipRectangleOffset + triangleHeight
            lineYBottom = self.sliderAreaTopOffset + self.sliderAreaHeight - self.clipRectangleOffset + triangleHeight
            painter.drawLine(timestamp, lineYTop, timestamp, lineYBottom)
            self._drawIsoscelesTriangle(painter, timestamp, triangleHeight, triangleHalfWidth, True, penColor, penColor)
            self._drawIsoscelesTriangle(painter, timestamp, triangleHeight, triangleHalfWidth, False, penColor, penColor)

    def _drawIsoscelesTriangle(self, painter: QStylePainter, timestamp: int, height: int, half_width: int, triangleBaseAtTop: bool, penColor: QColor, brushColor: QColor):
        painter.setRenderHint(QPainter.Antialiasing)
        baseYCoordinate = self.sliderAreaTopOffset + self.clipRectangleOffset - 2 if triangleBaseAtTop else self.sliderAreaTopOffset + self.clipRectangleOffset + self.regionHeight_ - 2
        apexYCoordinate = self.sliderAreaTopOffset + height + self.clipRectangleOffset if triangleBaseAtTop else self.sliderAreaTopOffset + self.sliderAreaHeight - self.clipRectangleOffset - height
        pointBase1 = QPoint(timestamp - half_width, baseYCoordinate)
        pointBase2 = QPoint(timestamp + half_width, baseYCoordinate)
        pointApex = QPoint(timestamp, apexYCoordinate)

        painter.setPen(penColor)
        painter.setBrush(brushColor)
        painter.drawPolygon(pointBase1, pointBase2, pointApex)

    def _drawCLipsEditMode_(self, painter: QStylePainter):
        glowAlpha = 150
        highlightColor = QColor(190, 85, 200, 255)
        glowColor = QColor(255, 255, 255, glowAlpha)
        maximumGradientSteps = copy(self.clips[self.currentRectangleIndex].rectangle.width())
        maximumGradientSteps = int(maximumGradientSteps)
        numberGradientSteps = min(self.numberGradientSteps, maximumGradientSteps)

        if self.freeCursorOnSide == self.CursorStates.cursorOnBeginSide:
            begin = copy(self.clips[self.currentRectangleIndex].rectangle.topLeft())
            end = copy(self.clips[self.currentRectangleIndex].rectangle.bottomLeft())
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

            begin = self.clips[self.currentRectangleIndex].rectangle.topLeft()
            end = self.clips[self.currentRectangleIndex].rectangle.bottomLeft()
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            painter.drawLine(begin, end)

        elif self.freeCursorOnSide == self.CursorStates.cursorOnEndSide:
            begin = copy(self.clips[self.currentRectangleIndex].rectangle.topRight())
            end = copy(self.clips[self.currentRectangleIndex].rectangle.bottomRight())
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

            begin = self.clips[self.currentRectangleIndex].rectangle.topRight()
            end = self.clips[self.currentRectangleIndex].rectangle.bottomRight()
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            painter.drawLine(begin, end)
        elif self.freeCursorOnSide == self.CursorStates.cursorIsInside:
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            brushColor = QColor(237, 242, 255, 150)
            painter.setBrush(brushColor)
            painter.setRenderHints(QPainter.HighQualityAntialiasing)
            painter.drawRoundedRect(self.clips[self.currentRectangleIndex].rectangle, 2, 2)

    # Mouse movement
    def _pixelPositionToSeconds(self, pixelPosition: int) -> float:
        return (pixelPosition - self.sliderAreaHorizontalOffset) * self.getScale()

    def _pixelPositionToQTime(self, pixelPosition: int) -> QTime:
        seconds = self._pixelPositionToSeconds(pixelPosition)

        milliseconds = int(round(1e3 * (seconds - int(seconds))))
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        seconds = int((seconds % 3600) % 60)

        # minutes = int(int(seconds) / 60)
        # hours = int(minutes / 60)
        # minutes -= minutes * 1
        # seconds -= minutes * 60
        time = QTime(hours, minutes, seconds, milliseconds)
        return time

    def _secondsToPixelPosition(self, seconds: float) -> int:
        return round(seconds / self.getScale() + self.sliderAreaHorizontalOffset)

    def _eventPositionToPointerPixelPosition(self, event_position):
        return self.clip(event_position, self.sliderAreaHorizontalOffset,
                         self.width() - self.sliderAreaHorizontalOffset)

    # def setPositionFromQTime(self):
    #     pass

    def setPositionFromSeconds(self, seconds: float) -> None:
        self.pointerPixelPosition = self._secondsToPixelPosition(seconds)
        self.pointerSecondsPosition = seconds
        # self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        keyPressed = QApplication.keyboardModifiers()
        mousePressed = QApplication.mouseButtons()
        self.position = event.pos()
        x = event.pos().x()
        if self.clicking and x:
            self.pointerPixelPosition = self._eventPositionToPointerPixelPosition(x)

        if (int(keyPressed) & Qt.ControlModifier) == Qt.ControlModifier and self.isIn:
            if self.state == self.RectangleEditState.freeState:
                self.freeCursorOnSide = self.mouseCursorState(event.pos())
                if self.freeCursorOnSide:
                    self.setCursor(Qt.SizeHorCursor)
                else:
                    self.unsetCursor()
            else:
                self.applyEvent(event)
        elif mousePressed == Qt.LeftButton:
            self.pointerPixelPosition = self._eventPositionToPointerPixelPosition(x)
            self.pointerSecondsPosition = self._pixelPositionToSeconds(self.pointerPixelPosition)
            self.sliderMoved.emit(self.pointerSecondsPosition)
            self.state = self.RectangleEditState.freeState
            self.freeCursorOnSide = 0
            self.unsetCursor()
        else:
            self.state = self.RectangleEditState.freeState
            self.freeCursorOnSide = 0
            self.unsetCursor()

        self.repaint()

    def _mousePressControlEvent(self, event: QMouseEvent):
        self.dragPosition = event.pos()
        self.dragRectPosition = self.clips[self.currentRectangleIndex].rectangle.topLeft()
        side = self.mouseCursorState(event.pos())
        if side == self.CursorStates.cursorOnBeginSide:
            self.state = self.RectangleEditState.beginSideEdit
        elif side == self.CursorStates.cursorOnEndSide:
            self.state = self.RectangleEditState.endSideEdit
        elif side == self.CursorStates.cursorIsInside:
            self.state = self.RectangleEditState.rectangleMove

        self.clicking = False

    def _mousePressAltEvent(self, event: QMouseEvent):
        index = self.mousePositionToClipIndex(event.pos())
        if index != -1:
            clip = self.videoListRef.videos[self.videoListRef.currentVideoIndex].clips[index]
            clipStartSeconds = 1e-3 * clip.timeStart.msecsSinceStartOfDay()
            self.setPositionFromSeconds(clipStartSeconds)
            self.parent.parent.playMediaTimeClip(index)
            self.clicking = False

    def _mousePressShiftEvent(self, event: QMouseEvent):
        index = self.mousePositionToClipIndex(event.pos())
        if index != -1:
            clip = self.videoListRef.videos[self.videoListRef.currentVideoIndex].clips[index]
            clipStartSeconds = 1e-3 * clip.timeStart.msecsSinceStartOfDay()
            self.setPositionFromSeconds(clipStartSeconds)

    def _mousePressLeftButtonEvent(self, event: QMouseEvent):
        x = event.pos().x()
        new_position = self._pixelPositionToSeconds(x)
        self.parent.parent.setPosition(new_position)
        self.clicking = True

    def mousePressEvent(self, event: QMouseEvent):
        if not self.parent.parent.mediaAvailable or not self.isIn or not self.isEnabled():
            super().mousePressEvent(event)
            return

        modifierPressed = QApplication.keyboardModifiers()
        if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
            self._mousePressControlEvent(event)
        elif (modifierPressed & Qt.AltModifier) == Qt.AltModifier:
            self._mousePressAltEvent(event)
        elif (modifierPressed & Qt.ShiftModifier) == Qt.ShiftModifier:
            self._mousePressShiftEvent(event)
        else:
            self._mousePressLeftButtonEvent(event)

        # super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not self.isIn:
            return

        modifierPressed = QApplication.keyboardModifiers()
        if event.button() == Qt.LeftButton and self.clicking:
            x = event.pos().x()
            self.pointerPixelPosition = self.clip(x, self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            self.pointerSecondsPosition = self._pixelPositionToSeconds(self.pointerPixelPosition)
        elif (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
            self.applyEvent(event)
            self.unsetCursor()
            currentVideoIndex = self.videoListRef.currentVideoIndex
            thumbnail = self.parent.parent.captureImage(self.parent.parent.currentMedia, self.videoListRef.currentVideoClipTimeStart(self.currentRectangleIndex))
            self.videoListRef.videos[currentVideoIndex].clips[self.currentRectangleIndex].thumbnail = thumbnail

            clip = self.videoListRef.videos[currentVideoIndex].clips[self.currentRectangleIndex]
            self.videoListRef.videos[currentVideoIndex].clips.pop(self.currentRectangleIndex)
            self.currentRectangleIndex = self.videoListRef.videos[currentVideoIndex].clips.bisect_right(clip)
            self.videoListRef.videos[currentVideoIndex].clips.add(clip)

            self.parent.parent.renderVideoClips()
            self.state = self.RectangleEditState.freeState
            self.freeCursorOnSide = self.CursorStates.cursorIsOutside
        elif len(self.videoListRef.videos[self.videoListRef.currentVideoIndex].clips) == 0:
            return

        self.sliderMoved.emit(self.pointerSecondsPosition)
        self.clicking = False  # Set clicking check to false
        self.repaint()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if not self.parent.parent.mediaAvailable or not self.isIn or not self.isEnabled():
            super().mousePressEvent(event)
            return

        modifierPressed = QApplication.keyboardModifiers()
        if (modifierPressed & Qt.ShiftModifier) == Qt.ShiftModifier:
            index = self.mousePositionToClipIndex(event.pos())
            if index != -1:
                clip = self.videoListRef.videos[self.videoListRef.currentVideoIndex].clips[index]
                clipEndSeconds = 1e-3 * clip.timeEnd.msecsSinceStartOfDay()
                self.setPositionFromSeconds(clipEndSeconds)

    def mouseCursorState(self, e_pos) -> CursorStates:
        if len(self.clips):
            for region_idx in range(len(self.clips)):
                if self.clips[region_idx].visibility:
                    self.begin = self.clips[region_idx].rectangle.topLeft()
                    self.end = self.clips[region_idx].rectangle.bottomRight()
                    y1, y2 = sorted([self.begin.y(), self.end.y()])
                    if y1 <= e_pos.y() <= y2:
                        self.currentRectangleIndex = region_idx
                        distance_mouse_begin = abs(self.begin.x() - e_pos.x())
                        distance_mouse_end = abs(self.end.x() - e_pos.x())
                        distance_begin_end = abs(self.begin.x() - self.end.x())
                        if distance_begin_end <= 10:
                            return self.CursorStates.cursorOnBeginSide if distance_mouse_begin < distance_mouse_end else self.CursorStates.cursorOnEndSide
                        elif distance_mouse_begin <= 5:
                            return self.CursorStates.cursorOnBeginSide
                        elif distance_mouse_end <= 5:
                            return self.CursorStates.cursorOnEndSide
                        elif self.begin.x() + 5 < e_pos.x() < self.end.x() - 5:
                            return self.CursorStates.cursorIsInside
        return self.CursorStates.cursorIsOutside

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.parent.parent.mediaAvailable:
            if event.angleDelta().y() > 0:
                self.parent.parent.mpvWidget.frameBackStep()
            else:
                self.parent.parent.mpvWidget.frameStep()
            self.parent.parent.setPlayButton(False)
            event.accept()

    def mousePositionToClipIndex(self, e_pos) -> int:
        if len(self.clips):
            for clipIndex in range(len(self.clips)):
                self.begin = self.clips[clipIndex].rectangle.topLeft()
                self.end = self.clips[clipIndex].rectangle.bottomRight()
                y1, y2 = sorted([self.begin.y(), self.end.y()])
                if y1 <= e_pos.y() <= y2 and self.begin.x() < e_pos.x() < self.end.x():
                    return clipIndex
        return -1

    def applyEvent(self, event):
        if self.state == self.RectangleEditState.beginSideEdit:
            rectangleLeftValue = max(event.x(), 0)
            self.clips[self.currentRectangleIndex].rectangle.setLeft(rectangleLeftValue)
            timeStart = self._pixelPositionToQTime(rectangleLeftValue)
            self.videoListRef.setCurrentVideoClipIndex(self.currentRectangleIndex)
            self.videoListRef.setCurrentVideoClipStartTime(timeStart)

        elif self.state == self.RectangleEditState.endSideEdit:
            rectangleRightValue = min(event.x(), self.width() - 1)
            self.clips[self.currentRectangleIndex].rectangle.setRight(rectangleRightValue)
            timeEnd = self._pixelPositionToQTime(rectangleRightValue)
            self.videoListRef.setCurrentVideoClipIndex(self.currentRectangleIndex)
            self.videoListRef.setCurrentVideoClipEndTime(timeEnd)

        elif self.state == self.RectangleEditState.rectangleMove:
            delta_value = event.x() - self.dragPosition.x()
            shift_value = self.dragRectPosition.x() + delta_value
            self.clips[self.currentRectangleIndex].rectangle.moveLeft(shift_value)

            rectangleLeftValue = max(self.clips[self.currentRectangleIndex].rectangle.left(), 0)
            rectangleRightValue = min(self.clips[self.currentRectangleIndex].rectangle.right(), self.width() - 1)
            timeStart = self._pixelPositionToQTime(rectangleLeftValue)
            timeEnd = self._pixelPositionToQTime(rectangleRightValue)

            self.videoListRef.setCurrentVideoClipIndex(self.currentRectangleIndex)
            self.videoListRef.setCurrentVideoClipStartTime(timeStart)
            self.videoListRef.setCurrentVideoClipEndTime(timeEnd)

    def enterEvent(self, event):
        self.isIn = True

    # Leave
    def leaveEvent(self, event):
        self.isIn = False
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

    # def keyPressEvent(self, a0):
    #     self.parent.keyPressEvent(a0)
