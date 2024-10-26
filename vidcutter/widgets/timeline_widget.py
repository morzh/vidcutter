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

    # class ClipTimestamps(Enum):

    class CursorStates(Enum):
        cursorIsOutsideClip = 0
        cursorIsAtClipStart = 1
        cursorIsAtClipEnd = 2
        cursorIsInsideClip = 3
        cursorIsAtTimestamp = 4

    class ClipEditMode(Enum):
        freeState = 1
        clipCreating = 2
        clipStart = 3
        clipEnd = 4
        clipRectangle = 5
        clipTimestamp = 6

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
        self.highlightPixelsThreshold = 5

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

        self.currentClipIndex = -1
        self.currentTimestampIndex = -1
        self.freeCursorState = 0
        self.state = self.ClipEditMode.freeState
        self.clip_rectangle_begin = QPoint()
        self.clip_rectangle_end = QPoint()
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

    def updateClip(self, clip_index: int, timeStart: QTime | None = None, timeEnd: QTime | None = None) -> None:
        clip = self.clips[clip_index]
        self.videoListRef.setCurrentVideoClipIndex(clip_index)

        if timeStart is not None:
            time_end = self.videoListRef[self.videoListRef.currentVideoIndex].clips[clip_index].timeEnd
            if time_end <= timeStart:
                timeStart = time_end

            self.videoListRef.setCurrentVideoClipStartTime(timeStart)
            time_start_seconds = timeStart.msecsSinceStartOfDay() * 1e-3
            pixelPositionStart = int(round(self._secondsToPixelPosition(time_start_seconds)))
            clip.rectangle.setLeft(pixelPositionStart)

            number_timestamps = len(clip.timestamps)
            for index_timestamp in range(number_timestamps):
                current_timestamp = self.videoListRef[self.videoListRef.currentVideoIndex].clips[clip_index].clip_timestamps[index_timestamp].timestamp
                current_timestamp_pixels = self._secondsToPixelPosition(time_start_seconds + current_timestamp.msecsSinceStartOfDay() * 1e-3)
                clip.timestamps[index_timestamp] = current_timestamp_pixels

        if timeEnd is not None:
            time_start = self.videoListRef[self.videoListRef.currentVideoIndex].clips[clip_index].timeStart
            if timeEnd <= time_start:
                timeEnd = time_start

            self.videoListRef.setCurrentVideoClipEndTime(timeEnd)
            pixelPositionEnd = int(round(self._secondsToPixelPosition(timeEnd.msecsSinceStartOfDay() * 1e-3)))
            clip.rectangle.setRight(pixelPositionEnd)

    def updateClipTimestamp(self, clip_index: int, timestamp_index: int, timestamp: QTime) -> None:
        self.videoListRef.setCurrentVideoClipIndex(clip_index)
        timestampPixelPosition = int(round(self._secondsToPixelPosition(timestamp.msecsSinceStartOfDay() * 1e-3)))
        self.clips[clip_index].timestamps[timestamp_index] = timestampPixelPosition

        clip_start_time = self.videoListRef[self.videoListRef.currentVideoIndex].clips[clip_index].timeStart
        relative_timestamp_milliseconds = timestamp.msecsSinceStartOfDay() - clip_start_time.msecsSinceStartOfDay()

        seconds = int(relative_timestamp_milliseconds * 1e-3)
        milliseconds = relative_timestamp_milliseconds - int(1e3 * seconds)
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        seconds = int((seconds % 3600) % 60)
        timestamp = QTime(hours, minutes, seconds, milliseconds)

        self.videoListRef[self.videoListRef.currentVideoIndex].clips[clip_index].clip_timestamps[timestamp_index].timestamp = timestamp

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
            currentTimestampPixelPosition = self._secondsToPixelPosition(videoClipTimeStart + timestamp.timestamp.msecsSinceStartOfDay() * 1e-3)
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
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self._drawFrame(painter)
        if self.isEnabled():
            painter.setFont(self.font)
            self._drawCutSegment(painter)
            self._drawTicks(painter)
            self._drawSlider(painter)
            self._drawVideoClips(painter)
            if self.currentClipIndex != -1 and self.freeCursorState:
                self._drawVideoClipsEditMode_(painter)
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

        painter.drawRoundedRect(self.sliderAreaHorizontalOffset, self.sliderAreaTopOffset, self.width() - 2 * self.sliderAreaHorizontalOffset, self.sliderAreaHeight, 3, 3)

    def _drawVideoClips(self, painter: QStylePainter) -> None:
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

    def _drawVideoClipsTimestampsEditMode_(self, painter: QStylePainter):
        pass

    def _drawVideoClipsEditMode_(self, painter: QStylePainter):
        glowAlpha = 150
        highlightColor = QColor(190, 85, 200, 255)
        glowColor = QColor(255, 255, 255, glowAlpha)
        currentClipRectangle = self.clips[self.currentClipIndex].rectangle
        maximumGradientSteps = max(copy(currentClipRectangle.width()), 1)
        # maximumGradientSteps = int(maximumGradientSteps)
        numberGradientSteps = min(self.numberGradientSteps, maximumGradientSteps)

        if self.freeCursorState == self.CursorStates.cursorIsAtClipStart:
            begin = copy(self.clips[self.currentClipIndex].rectangle.topLeft())
            end = copy(self.clips[self.currentClipIndex].rectangle.bottomLeft())
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

            begin = currentClipRectangle.topLeft()
            end = currentClipRectangle.bottomLeft()
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            painter.drawLine(begin, end)

        elif self.freeCursorState == self.CursorStates.cursorIsAtClipEnd:
            begin = copy(currentClipRectangle.topRight())
            end = copy(currentClipRectangle.bottomRight())
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

            begin = currentClipRectangle.topRight()
            end = currentClipRectangle.bottomRight()
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            painter.drawLine(begin, end)

        elif self.freeCursorState == self.CursorStates.cursorIsInsideClip:
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            brushColor = QColor(237, 242, 255, 150)
            painter.setBrush(brushColor)
            painter.setRenderHints(QPainter.HighQualityAntialiasing)
            painter.drawRoundedRect(currentClipRectangle, 2, 2)
        elif self.freeCursorState == self.CursorStates.cursorIsAtTimestamp:
            begin = copy(currentClipRectangle.topRight())
            end = copy(currentClipRectangle.bottomRight())
            step = int(glowAlpha / numberGradientSteps)

            begin.setX(self.clips[self.currentClipIndex].timestamps[self.currentTimestampIndex])
            end.setX(self.clips[self.currentClipIndex].timestamps[self.currentTimestampIndex])
            coordinateX = end.x()
            for index_step in range(numberGradientSteps):
                begin.setX(coordinateX - index_step)
                end.setX(coordinateX - index_step)
                glowColor.setAlpha(glowAlpha - step * index_step)
                painter.setPen(QPen(glowColor, 1, Qt.SolidLine))
                painter.drawLine(begin, end)

            begin.setX(self.clips[self.currentClipIndex].timestamps[self.currentTimestampIndex])
            end.setX(self.clips[self.currentClipIndex].timestamps[self.currentTimestampIndex])
            coordinateX = end.x()
            for index_step in range(numberGradientSteps):
                begin.setX(coordinateX + index_step)
                end.setX(coordinateX + index_step)
                glowColor.setAlpha(glowAlpha - step * index_step)
                painter.setPen(QPen(glowColor, 1, Qt.SolidLine))
                painter.drawLine(begin, end)

            begin.setX(self.clips[self.currentClipIndex].timestamps[self.currentTimestampIndex])
            end.setX(self.clips[self.currentClipIndex].timestamps[self.currentTimestampIndex])
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            painter.drawLine(begin, end)

    # Mouse movement
    def _pixelPositionToSeconds(self, pixelPosition: int) -> float:
        return (pixelPosition - self.sliderAreaHorizontalOffset) * self.getScale()

    def _pixelPositionToQTime(self, pixelPosition: int) -> QTime:
        seconds = self._pixelPositionToSeconds(pixelPosition)

        milliseconds = int(round(1e3 * (seconds - int(seconds))))
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        seconds = int((seconds % 3600) % 60)
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
            if self.state == self.ClipEditMode.freeState:
                self.freeCursorState = self.mouseCursorState(event.pos())
                if self.freeCursorState:
                    self.setCursor(Qt.SizeHorCursor)
                else:
                    self.unsetCursor()
            else:
                self.applyEvent(event)
        elif mousePressed == Qt.LeftButton:
            self.pointerPixelPosition = self._eventPositionToPointerPixelPosition(x)
            self.pointerSecondsPosition = self._pixelPositionToSeconds(self.pointerPixelPosition)
            self.sliderMoved.emit(self.pointerSecondsPosition)
            self.state = self.ClipEditMode.freeState
            self.freeCursorState = 0
            self.unsetCursor()
        else:
            self.state = self.ClipEditMode.freeState
            self.freeCursorState = 0
            self.unsetCursor()

        self.repaint()

    def _mousePressControlEvent(self, event: QMouseEvent):
        self.dragPosition = event.pos()
        self.dragRectPosition = self.clips[self.currentClipIndex].rectangle.topLeft()

        side = self.mouseCursorState(event.pos())
        if side == self.CursorStates.cursorIsAtClipStart:
            self.state = self.ClipEditMode.clipStart
        elif side == self.CursorStates.cursorIsAtClipEnd:
            self.state = self.ClipEditMode.clipEnd
        elif side == self.CursorStates.cursorIsInsideClip:
            self.state = self.ClipEditMode.clipRectangle
        elif side == self.CursorStates.cursorIsAtTimestamp:
            self.state = self.ClipEditMode.clipTimestamp

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
        if event.button() == Qt.LeftButton and (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
            self._mousePressControlEvent(event)
        elif event.button() == Qt.LeftButton and (modifierPressed & Qt.AltModifier) == Qt.AltModifier:
            self._mousePressAltEvent(event)
        elif event.button() == Qt.LeftButton and (modifierPressed & Qt.ShiftModifier) == Qt.ShiftModifier:
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

        elif event.button() == Qt.RightButton and modifierPressed == Qt.ShiftModifier:
            self.addTimestampToClip(event)

        elif event.button() == Qt.LeftButton and modifierPressed == Qt.ControlModifier:
            self.applyEvent(event)
            self.videoListRef[self.videoListRef.currentVideoIndex].cleanClipsTimestamps()
            self.unsetCursor()

            currentVideoIndex = self.videoListRef.currentVideoIndex
            thumbnail = self.parent.parent.captureImage(self.parent.parent.currentMedia, self.videoListRef.currentVideoClipTimeStart(self.currentClipIndex))
            self.videoListRef.videos[currentVideoIndex].clips[self.currentClipIndex].thumbnail = thumbnail

            clip = self.videoListRef.videos[currentVideoIndex].clips[self.currentClipIndex]
            self.videoListRef.videos[currentVideoIndex].clips.pop(self.currentClipIndex)
            self.currentClipIndex = self.videoListRef.videos[currentVideoIndex].clips.bisect_right(clip)
            self.videoListRef.videos[currentVideoIndex].clips.add(clip)

            self.videoListRef[self.videoListRef.currentVideoIndex].cleanClips()
            if not len(self.videoListRef[self.videoListRef.currentVideoIndex]):
                self.currentClipIndex = -1

            self.parent.parent.renderVideoClips()
            self.state = self.ClipEditMode.freeState
            self.freeCursorState = self.CursorStates.cursorIsOutsideClip


        self.sliderMoved.emit(self.pointerSecondsPosition)
        self.clicking = False  # Set clicking check to false
        self.update()
        self.repaint()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if not self.parent.parent.mediaAvailable or not self.isIn or not self.isEnabled():
            super().mousePressEvent(event)
            return

        modifierPressed = QApplication.keyboardModifiers()
        if event.button() == Qt.LeftButton and modifierPressed == Qt.ShiftModifier:
            index = self.mousePositionToClipIndex(event.pos())
            if index != -1:
                clip = self.videoListRef.videos[self.videoListRef.currentVideoIndex].clips[index]
                clipEndSeconds = 1e-3 * clip.timeEnd.msecsSinceStartOfDay()
                self.setPositionFromSeconds(clipEndSeconds)


    def mouseCursorState(self, mouse_position) -> CursorStates:
        if len(self.clips):
            mouse_horizontal_position = mouse_position.x()
            mouse_vertical_position = mouse_position.y()
            for clip_index in range(len(self.clips)):
                if self.clips[clip_index].visibility:
                    self.clip_rectangle_begin = self.clips[clip_index].rectangle.topLeft()
                    self.clip_rectangle_end = self.clips[clip_index].rectangle.bottomRight()
                    y1, y2 = sorted([self.clip_rectangle_begin.y(), self.clip_rectangle_end.y()])
                    x1, x2 = sorted([self.clip_rectangle_begin.x(), self.clip_rectangle_end.x()])

                    if y1 <= mouse_vertical_position <= y2 and x1 <= mouse_horizontal_position <= x2:
                        self.currentClipIndex = clip_index

                        rectangle_timestamps_data = [self.clips[clip_index].rectangle.left()]
                        rectangle_timestamps_data.extend(self.clips[clip_index].timestamps)
                        rectangle_timestamps_data.append(self.clips[clip_index].rectangle.right())
                        # print(rectangle_timestamps_data)

                        rectangle_timestamps_distances = [None] * len(rectangle_timestamps_data)
                        indices_selection_threshold = []
                        minimal_distance_index = -1
                        minimal_distance = abs(self.clip_rectangle_begin.x() - self.clip_rectangle_end.x()) + 2

                        for timestamp_index in range(len(rectangle_timestamps_data)):
                            current_distance = abs(rectangle_timestamps_data[timestamp_index] - mouse_position.x())
                            rectangle_timestamps_distances[timestamp_index] = current_distance
                            if current_distance < self.highlightPixelsThreshold:
                                indices_selection_threshold.append(timestamp_index)
                            if current_distance < minimal_distance:
                                minimal_distance = current_distance
                                minimal_distance_index = timestamp_index

                        if len(indices_selection_threshold) == 0:
                            return self.CursorStates.cursorIsInsideClip
                        elif len(indices_selection_threshold) == 1:
                            if minimal_distance_index == 0:
                                return self.CursorStates.cursorIsAtClipStart
                            elif minimal_distance_index == len(rectangle_timestamps_data) - 1:
                                return self.CursorStates.cursorIsAtClipEnd
                            else:
                                self.currentTimestampIndex = minimal_distance_index - 1
                                return self.CursorStates.cursorIsAtTimestamp
                        elif len(indices_selection_threshold) > 0:
                            if minimal_distance_index == 0:
                                return self.CursorStates.cursorIsAtClipStart
                            elif minimal_distance_index == len(rectangle_timestamps_data) - 1:
                                return self.CursorStates.cursorIsAtClipEnd
                            else:
                                self.currentTimestampIndex = minimal_distance_index - 1
                                return self.CursorStates.cursorIsAtTimestamp

        return self.CursorStates.cursorIsOutsideClip

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
                self.clip_rectangle_begin = self.clips[clipIndex].rectangle.topLeft()
                self.clip_rectangle_end = self.clips[clipIndex].rectangle.bottomRight()
                y1, y2 = sorted([self.clip_rectangle_begin.y(), self.clip_rectangle_end.y()])
                if y1 <= e_pos.y() <= y2 and self.clip_rectangle_begin.x() < e_pos.x() < self.clip_rectangle_end.x():
                    return clipIndex
        return -1

    def addTimestampToClip(self, event):
        mouse_position = event.pos()
        clip_index = self.mousePositionToClipIndex(mouse_position)
        if clip_index > -1:
            clip_start_pixels = self.clips[clip_index].rectangle.left()
            timestamp = self._pixelPositionToQTime(mouse_position.x() - clip_start_pixels + self.sliderAreaHorizontalOffset)
            clip_timestamp = VideoClipTimestamps(timestamp)
            self.videoListRef[self.videoListRef.currentVideoIndex].clips[clip_index].clip_timestamps.append(clip_timestamp)
            self.clips[clip_index].timestamps.append(mouse_position.x())

    def applyEvent(self, event):
        if self.state == self.ClipEditMode.clipStart:
            rectangleLeftValue = max(event.x(), 0)
            timeStart = self._pixelPositionToQTime(rectangleLeftValue)
            self.updateClip(self.currentClipIndex, timeStart=timeStart)

        elif self.state == self.ClipEditMode.clipEnd:
            rectangleRightValue = min(event.x(), self.width() - self.sliderAreaHorizontalOffset)
            timeEnd = self._pixelPositionToQTime(rectangleRightValue)
            self.updateClip(self.currentClipIndex, timeEnd=timeEnd)

        elif self.state == self.ClipEditMode.clipRectangle:
            delta_value = event.x() - self.dragPosition.x()
            shift_value = self.dragRectPosition.x() + delta_value
            # rectangle_left_value = self.clips[self.currentClipIndex].rectangle.left()
            rectangle_width = self.clips[self.currentClipIndex].rectangle.width()
            shift_value = self.clamp(shift_value, self.sliderAreaHorizontalOffset, self.width() - rectangle_width - self.sliderAreaHorizontalOffset)
            self.clips[self.currentClipIndex].rectangle.moveLeft(shift_value)

            rectangleLeftValue = self.clips[self.currentClipIndex].rectangle.left()
            rectangleRightValue = self.clips[self.currentClipIndex].rectangle.right()

            timeStart = self._pixelPositionToQTime(rectangleLeftValue)
            timeEnd = self._pixelPositionToQTime(rectangleRightValue)
            self.updateClip(self.currentClipIndex, timeStart=timeStart, timeEnd=timeEnd)

        elif self.state == self.ClipEditMode.clipTimestamp:
            absoluteTimestampPixelValue = max(event.x(), 0)
            absolute_timestamp = self._pixelPositionToQTime(absoluteTimestampPixelValue)
            self.updateClipTimestamp(self.currentClipIndex, self.currentTimestampIndex, absolute_timestamp)

    @staticmethod
    def clamp(value, smallest, largest):
        return max(smallest, min(value, largest))

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

    @staticmethod
    def getTimeString(seconds, return_milliseconds=False):
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
