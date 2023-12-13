#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
from copy import copy
from enum import Enum

import PySide2
from PyQt5.QtCore import QEvent, QObject, QRect, Qt, pyqtSlot, QPoint
from PyQt5.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPaintEvent, QPalette, QPen, QWheelEvent, QPainter
from PyQt5.QtWidgets import (qApp, QProgressBar, QSlider, QStyle, QStyleFactory, QStyleOptionSlider, QStylePainter, QApplication)

from vidcutter.VideoItemClip import VideoItemClip


class TimelineWidget(QSlider):
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
        super(TimelineWidget, self).__init__(parent)
        self.parent = parent
        self.dragRectPosition = QPoint()
        self.dragPosition = QPoint()
        self.logger = logging.getLogger(__name__)
        self.theme = self.parent.theme
        self._styles = '''
        QSlider:horizontal {{
            margin: 16px 8px 32px;
            height: {sliderHeight}px;
        }}
        QSlider::sub-page:horizontal {{
            border: none;
            background: {subpageBgColor};
            height: {subpageHeight}px;
            position: absolute;
            left: 0;
            right: 0;
            margin: 0;
            margin-left: {subpageLeftMargin}px;
        }}
        QSlider::add-page:horizontal {{
            border: none;
            background: transparent;
        }}
        QSlider::handle:horizontal {{
            border: none;
            border-radius: 0;
            background: transparent url(:images/{handleImage}) no-repeat top center;
            width: 15px;
            height: {handleHeight}px;
            margin: -12px -8px -20px;
        }}'''
        self._progressbars = []
        self._regions = []
        self._regionsVisibility = []
        self._regionHeight = 20
        self._regionSelected = -1
        self._handleHover = False
        self._cutStarted = False
        self.showThumbs = True
        self.thumbnailsOn = False
        self.offset = 8  # 6
        self.setOrientation(Qt.Horizontal)
        self.setObjectName('videoslider')
        self.setStatusTip('Set clip start and end points')
        self.setFocusPolicy(Qt.StrongFocus)
        self.setRange(0, 0)
        self.setSingleStep(1)
        self.setTickInterval(100000)
        self.setTracking(True)
        self.setMouseTracking(True)
        self.setTickPosition(QSlider.TicksBelow)
        self.restrictValue = 0
        self.valueChanged.connect(self.on_valueChanged)
        self.rangeChanged.connect(self.on_rangeChanged)
        self.installEventFilter(self)

        self.freeCursorOnSide = 0
        self.state = self.RectangleEditState.freeState
        self.begin = QPoint()
        self.end = QPoint()
        self.currentRectangleIndex = -1

        self.widgetWidth = int()
        self.frameCounterMaximum = -1
        self.numberGradientSteps = 50
        self.regionOutlineWidth = 4
        self.baseMaximum = 0

    def initAttributes(self):
        self.setEnabled(False)
        self.setTracking(True)
        self.setMouseTracking(True)
        self.setUpdatesEnabled(False)
        # self.setMaximum(self.parent.parent.size().width() - 20)

    def initSliderParameters(self) -> None:
        self.widgetWidth = self.size().width()
        self.frameCounterMaximum = self.parent.frameCounter.maximum()

    def initStyle(self) -> None:
        bground = 'rgba(200, 213, 236, 0.85)' if self._cutStarted else 'transparent'
        height = 25
        handle = 'handle-select.png' if self._handleHover else 'handle.png'
        handle_height = 0
        margin = 0
        timeline = ''
        self._regionHeight = 19
        if not self.thumbnailsOn:
            '''
            if self.parent.thumbnailsButton.isChecked():
                timeline = 'background: #000 url(:images/filmstrip.png) repeat-x left;'
            else:
                timeline = 'background: #000 url(:images/filmstrip-nothumbs.png) repeat-x left;'
                handle_height = 42
                height = 15
                handle = 'handle-nothumbs-select.png' if self._handleHover else 'handle-nothumbs.png'
                self._regionHeight = 12
            '''
            self._styles += '''
            QSlider::groove:horizontal {{
                border: 1px ridge #444;
                height: {sliderHeight}px;
                margin: 0;
                {timelineBackground}
            }}'''
        else:
            self._styles += '''
            QSlider::groove:horizontal {{
                border: none;
                height: {sliderHeight}px;
                margin: 0;
            }}'''
        if self._cutStarted:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            control = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self)
            margin = control.x()
        self.setStyleSheet(self._styles.format(
            sliderHeight=height,
            subpageBgColor=bground,
            subpageHeight=height + 2,
            subpageLeftMargin=margin,
            handleImage=handle,
            handleHeight=handle_height,
            timelineBackground=timeline))

    # def maximum(self):
    #     return self.parent.factor * super().maximum()

    def sliderPositionFromValue(self, minimum: int, maximum: int, logicalValue: int, span: int, upsideDown: bool = ...) -> int:
        return int(float(logicalValue) / float(maximum - minimum) * span)

    def sliderValueFromPosition(self, minimum: int, maximum: int, position, span: int) -> int:
        return int(position / span * float(maximum - minimum))

    def setRestrictValue(self, value: int = 0, force: bool = False) -> None:
        self.restrictValue = value
        if value > 0 or force:
            self._cutStarted = True
            self._handleHover = True
        else:
            self._cutStarted = False
            self._handleHover = False
        self.initStyle()

    def renderVideoSegments(self, clips: list[VideoItemClip]):
        self.clearRegions()
        for videoClip in clips:
            clipStart = videoClip.timeStart.msecsSinceStartOfDay()
            clipEnd = videoClip.timeEnd.msecsSinceStartOfDay()
            clipVisibility = videoClip.visibility
            self.addRegion(clipStart, clipEnd, clipVisibility)
        self.update()

    def drawTicks_(self, painter: QStylePainter):
        if self.tickPosition() != QSlider.NoTicks:
            x = 8
            for i in range(self.minimum(), self.width(), 8):
                if i % 5 == 0:
                    h, w, z = 16, 1, 13
                else:
                    h, w, z = 8, 1, 23
                tickColor = QColor('#8F8F8F' if self.theme == 'dark' else '#444')
                pen = QPen(tickColor)  # , Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                pen.setWidthF(w)
                painter.setPen(pen)
                if self.tickPosition() in (QSlider.TicksBothSides, QSlider.TicksAbove):
                    y = self.rect().top() + z
                    painter.drawLine(x, y, x, y + h)
                if self.tickPosition() in (QSlider.TicksBothSides, QSlider.TicksBelow):
                    y = self.rect().bottom() - z
                    painter.drawLine(x, y, x, y - h)
                    if self.parent.mediaAvailable and i % 10 == 0 and (x + 4 + 50) < self.width():
                        painter.setPen(Qt.white if self.theme == 'dark' else Qt.black)
                        timecode = self.sliderValueFromPosition(self.minimum(), self.maximum(), x - self.offset, self.width() - (self.offset * 2))
                        # timecode = int(x / (self.maximum() - self.minimum()) * self.width())
                        # timecode = x / (self.width()) * self.parent.duration
                        timecode = self.parent.delta2QTime(timecode).toString(self.parent.runtimeformat)
                        painter.drawText(x + 4, y + 6, timecode)
                if x + 30 > self.width():
                    break
                x += 15

    def drawClips_(self, painter: QStylePainter, opt: QStyleOptionSlider):
        # opt = QStyleOptionSlider()
        opt.subControls = QStyle.SC_SliderGroove
        painter.drawComplexControl(QStyle.CC_Slider, opt)
        videoIndex = self.parent.videoList.currentVideoIndex
        if not len(self._progressbars):
            if len(self._regions) == len(self._regionsVisibility):  # should always be true
                visible_region = self.visibleRegion().boundingRect()
                for index, (rect, rectViz) in enumerate(zip(self._regions, self._regionsVisibility)):
                    if rectViz == 0:
                        continue
                    rect.setY(int((self.height() - self._regionHeight) / 2) - 8)
                    rect.setHeight(self._regionHeight)
                    rectClass = rect.adjusted(0, 0, 0, 0)
                    brushColor = QColor(150, 190, 78, 150) if self._regions.index(rect) == self._regionSelected else QColor(237, 242, 255, 150)
                    painter.setBrush(brushColor)
                    painter.setPen(QColor(50, 50, 50, 170))
                    painter.setRenderHints(QPainter.HighQualityAntialiasing)
                    painter.drawRoundedRect(rect, 2, 2)
                    painter.setFont(QFont('Noto Sans', 13 if sys.platform == 'darwin' else 11, QFont.SansSerif))
                    painter.setPen(Qt.black if self.theme == 'dark' else Qt.white)
                    rectClass = rectClass.intersected(visible_region)
                    rectClass = rectClass.adjusted(5, 0, -5, 0)
                    actionClassIndex = self.parent.videoList[videoIndex].clips[index].actionClassIndex
                    if actionClassIndex == -1:
                        actionClassLabel = copy(self.parent.videoList.actionClassUnknownLabel)
                    else:
                        actionClassLabel = copy(self.parent.videoList.actionClassesLabels[actionClassIndex])
                    painter.drawText(rectClass, Qt.AlignBottom | Qt.AlignLeft, actionClassLabel)
        opt.activeSubControls = opt.subControls = QStyle.SC_SliderHandle
        painter.drawComplexControl(QStyle.CC_Slider, opt)

    def drawCLipsEditMode_(self, painter: QStylePainter):
        glowAlpha = 150
        highlightColor = QColor(190, 85, 200, 255)
        glowColor = QColor(255, 255, 255, glowAlpha)
        maximumGradientSteps = copy(self._regions[self.currentRectangleIndex].width())
        maximumGradientSteps = int(maximumGradientSteps)
        numberGradientSteps = min(self.numberGradientSteps, maximumGradientSteps)

        if self.freeCursorOnSide == self.CursorStates.cursorOnBeginSide:
            begin = copy(self._regions[self.currentRectangleIndex].topLeft())
            end = copy(self._regions[self.currentRectangleIndex].bottomLeft())
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

            begin = self._regions[self.currentRectangleIndex].topLeft()
            end = self._regions[self.currentRectangleIndex].bottomLeft()
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            painter.drawLine(begin, end)

        elif self.freeCursorOnSide == self.CursorStates.cursorOnEndSide:
            begin = copy(self._regions[self.currentRectangleIndex].topRight())
            end = copy(self._regions[self.currentRectangleIndex].bottomRight())
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

            begin = self._regions[self.currentRectangleIndex].topRight()
            end = self._regions[self.currentRectangleIndex].bottomRight()
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            painter.drawLine(begin, end)
        elif self.freeCursorOnSide == self.CursorStates.cursorIsInside:
            painter.setPen(QPen(highlightColor, self.regionOutlineWidth, Qt.SolidLine))
            brushColor = QColor(237, 242, 255, 150)
            painter.setBrush(brushColor)
            painter.setRenderHints(QPainter.HighQualityAntialiasing)
            painter.drawRoundedRect(self._regions[self.currentRectangleIndex], 2, 2)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QStylePainter(self)
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        font = painter.font()
        font.setPixelSize(11)
        painter.setFont(font)

        self.drawTicks_(painter)
        self.drawClips_(painter, opt)

        if not self.freeCursorOnSide:
            return

        self.drawCLipsEditMode_(painter)

    def setRegionVizivility(self, index, state):
        if len(self._regionsVisibility) > 0:
            self._regionsVisibility[index] = state
            self.update()

    def mouseCursorState(self, e_pos) -> CursorStates:
        if len(self._regions) > 0:
            for region_idx in range(len(self._regions)):
                if self._regionsVisibility[region_idx]:
                    self.begin = self._regions[region_idx].topLeft()
                    self.end = self._regions[region_idx].bottomRight()
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

    def mouseCursorRegionIndex(self, e_pos):
        if len(self._regions) > 0:
            for region_idx in range(len(self._regions)):
                self.begin = self._regions[region_idx].topLeft()
                self.end = self._regions[region_idx].bottomRight()
                y1, y2 = sorted([self.begin.y(), self.end.y()])
                if y1 <= e_pos.y() <= y2 and self.begin.x() < e_pos.x() < self.end.x():
                    return region_idx

    def addRegion(self, start: int, end: int, visibility=2) -> None:
        regionStart = self.sliderPositionFromValue(self.minimum(), self.maximum(), start - self.offset, self.width() - (self.offset * 2))
        regionEnd = self.sliderPositionFromValue(self.minimum(), self.maximum(), end - self.offset, self.width() - (self.offset * 2))
        # regionStart = int(start / (1e3 * self.parent.duration) * self.width())
        # regionEnd = int(end / (1e3 * self.parent.duration) * self.width())
        width = regionEnd - regionStart
        y = int((self.height() - self._regionHeight) / 2)
        height = self._regionHeight
        self._regions.append(QRect(regionStart + self.offset, y - 8, width, height))
        self._regionsVisibility.append(visibility)
        self.update()

    def switchRegions(self, index1: int, index2: int) -> None:
        region = self._regions.pop(index1)
        regionVisibility = self._regionsVisibility.pop(index1)
        self._regions.insert(index2, region)
        self._regionsVisibility.insert(index2, regionVisibility)
        self.update()

    def selectRegion(self, clipindex: int) -> None:
        self._regionSelected = clipindex
        self.update()

    def clearRegions(self) -> None:
        self._regions.clear()
        self._regionsVisibility.clear()
        self._regionSelected = -1
        self.update()

    # @pyqtSlot(int)
    # def showProgress(self, steps: int) -> None:
    #     if len(self._regions):
    #         [self._progressbars.append(SliderProgress(steps, rect, self)) for rect in self._regions]
    #     else:
    #         self.parent.videoClipsList.showProgress(steps)

    @pyqtSlot()
    @pyqtSlot(int)
    def updateProgress(self, region: int = None) -> None:
        if len(self._regions):
            if region is None:
                [progress.setValue(progress.value() + 1) for progress in self._progressbars]
            else:
                self._progressbars[region].setValue(self._progressbars[region].value() + 1)
        else:
            self.parent.videoClipsList.updateProgress(region)

    @pyqtSlot()
    def clearProgress(self) -> None:
        for progress in self._progressbars:
            progress.hide()
            progress.deleteLater()
        self.parent.videoClipsList.clearProgress()
        self._progressbars.clear()

    @pyqtSlot(list)
    def buildTimeline(self, thumbs: list) -> None:
        self.initStyle()
        # self.parent.videoSliderWidget.setLoader(False)
        if self.parent.newproject:
            self.parent.renderVideoClips()
            self.parent.newproject = False

    def errorHandler(self, error: str) -> None:
        self.logger.error(error)
        sys.stderr.write(error)

    @pyqtSlot(int)
    def on_valueChanged(self, value: int) -> None:
        # print('on_valueChanged::value:', value, 'on_valueChanged::self.restrictValue', self.restrictValue)
        if value < self.restrictValue:
            self.setSliderPosition(self.restrictValue)

    @pyqtSlot()
    def on_rangeChanged(self) -> None:
        # self.parent.videoSliderWidget.setLoader(False)
        pass

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.parent.mediaAvailable:
            if event.angleDelta().y() > 0:
                self.parent.mpvWidget.frameBackStep()
            else:
                self.parent.mpvWidget.frameStep()
            self.parent.setPlayButton(False)
            event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        qApp.sendEvent(self.parent, event)

    def applyEvent(self, event):
        if self.state == self.RectangleEditState.beginSideEdit:
            rectangle_left_value = max(event.x(), 0)
            self._regions[self.currentRectangleIndex].setLeft(rectangle_left_value)
            value_begin = self.sliderValueFromPosition(self.minimum(), self.maximum(), rectangle_left_value - self.offset, self.width() - (self.offset * 2))
            time_start = self.parent.delta2QTime(value_begin)
            self.parent.videoList.setCurrentVideoClipIndex(self.currentRectangleIndex)
            # self.parent.videoList.videos.pop(self.currentRectangleIndex)
            self.parent.videoList.setCurrentVideoClipStartTime(time_start)
        elif self.state == self.RectangleEditState.endSideEdit:
            rectangle_right_value = min(event.x(), self.width() - 1)
            self._regions[self.currentRectangleIndex].setRight(rectangle_right_value)
            value = self.sliderValueFromPosition(self.minimum(), self.maximum(), rectangle_right_value - self.offset, self.width() - (self.offset * 2))
            time = self.parent.delta2QTime(value)
            self.parent.videoList.setCurrentVideoClipIndex(self.currentRectangleIndex)
            self.parent.videoList.setCurrentVideoClipEndTime(time)
        elif self.state == self.RectangleEditState.rectangleMove:
            delta_value = event.x() - self.dragPosition.x()
            shift_value = self.dragRectPosition.x() + delta_value
            self._regions[self.currentRectangleIndex].moveLeft(shift_value)
            rectangle_left_value = max(self._regions[self.currentRectangleIndex].left(), 0)
            rectangle_right_value = min(self._regions[self.currentRectangleIndex].right(), self.width() - 1)
            value_begin = self.sliderValueFromPosition(self.minimum(), self.maximum(), rectangle_left_value - self.offset, self.width() - (self.offset * 2))
            value_end = self.sliderValueFromPosition(self.minimum(), self.maximum(), rectangle_right_value - self.offset, self.width() - (self.offset * 2))
            self.parent.videoList.setCurrentVideoClipIndex(self.currentRectangleIndex)
            self.parent.videoList.setCurrentVideoClipStartTime(self.parent.delta2QTime(value_begin))
            self.parent.videoList.setCurrentVideoClipEndTime(self.parent.delta2QTime(value_end))

    def eventFilter(self, obj: QObject, event: QMouseEvent) -> bool:
        modifierPressed = QApplication.keyboardModifiers()
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
                self.applyEvent(event)
                self.unsetCursor()
            if len(self.parent.videoList.videos[self.parent.videoList.currentVideoIndex].clips) == 0:
                return False

            # print('self.currentRectangleIndex', self.currentRectangleIndex)
            thumbnail = self.parent.captureImage(self.parent.currentMedia, self.parent.videoList.currentVideoClipTimeStart(self.currentRectangleIndex))
            self.parent.videoList.videos[self.parent.videoList.currentVideoIndex].clips[self.currentRectangleIndex].thumbnail = thumbnail

            clip = self.parent.videoList.videos[self.parent.videoList.currentVideoIndex].clips[self.currentRectangleIndex]
            self.parent.videoList.videos[self.parent.videoList.currentVideoIndex].clips.pop(self.currentRectangleIndex)
            self.currentRectangleIndex = self.parent.videoList.videos[self.parent.videoList.currentVideoIndex].clips.bisect_right(clip)
            self.parent.videoList.videos[self.parent.videoList.currentVideoIndex].clips.add(clip)

            self.parent.renderVideoClips()
            self.state = self.RectangleEditState.freeState
            self.freeCursorOnSide = 0
            self.repaint()

        elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
                self.dragPosition = event.pos()
                self.dragRectPosition = self._regions[self.currentRectangleIndex].topLeft()
                side = self.mouseCursorState(event.pos())
                if side == self.CursorStates.cursorOnBeginSide:
                    self.state = self.RectangleEditState.beginSideEdit
                elif side == self.CursorStates.cursorOnEndSide:
                    self.state = self.RectangleEditState.endSideEdit
                elif side == self.CursorStates.cursorIsInside:
                    self.state = self.RectangleEditState.rectangleMove
            elif self.parent.mediaAvailable and self.isEnabled():
                new_position = self.sliderValueFromPosition(self.minimum(), self.maximum(), event.x() - self.offset, self.width() - (self.offset * 2))
                # new_position = int(event.x() / self.width() * (self.maximum() - self.minimum()))
                self.setValue(new_position)
                self.parent.setPosition(new_position)
                self.parent.parent.mousePressEvent(event)

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

        elif event.type() == QEvent.MouseButtonPress and (modifierPressed & Qt.AltModifier) == Qt.AltModifier:
            self.mouseCursorRegionIndex(event)

        return super(TimelineWidget, self).eventFilter(obj, event)

    def mousePressEvent(self, event):
        modifierPressed = QApplication.keyboardModifiers()
        if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier and event.button() == Qt.LeftButton:
            # event.accept()
            return
        elif (modifierPressed & Qt.AltModifier) == Qt.AltModifier and event.button() == Qt.LeftButton:
            index = self.mouseCursorRegionIndex(event)
            clip = self.parent.videoList.videos[self.parent.videoList.currentVideoIndex].clips[index]
            self.setSliderPosition(clip.timeStart.msecsSinceStartOfDay())
            self.parent.playMediaTimeClip(index)
            # event.accept()
        super().mousePressEvent(event)


class SliderProgress(QProgressBar):
    def __init__(self, steps: int, geometry: QRect, parent=None):
        super(SliderProgress, self).__init__(parent)
        self.setStyle(QStyleFactory.create('Fusion'))
        self.setRange(0, steps)
        self.setValue(0)
        self.setGeometry(geometry)
        palette = self.palette()
        palette.setColor(QPalette.Highlight, QColor(100, 44, 104))
        self.setPalette(palette)
        self.show()
