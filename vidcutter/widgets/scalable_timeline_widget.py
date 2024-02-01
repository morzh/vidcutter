#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from base64 import b64encode

import sys
from copy import copy

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint, QLine, QRect, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QKeyEvent, QColor, QFont, QBrush, QPalette, QPen, QPolygon, QPainterPath, QPixmap
from PyQt5.QtWidgets import QStyle, QStylePainter, QWidget, QStyleOptionSlider, QScrollArea, QVBoxLayout, QPushButton, QHBoxLayout, QLabel


class TimeLine(QWidget):
    sliderMoved = pyqtSignal(float)

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


    def positionChanged(self):
        print('positionChanged')

    def initAttributes(self):
        self.setFixedWidth(self.length)
        self.setFixedHeight(self.timeLineHeight)
        # Set Background
        palette = QPalette()
        palette.setColor(QPalette.Background, self.backgroundColor)
        self.setPalette(palette)

    def drawTicks_(self, painter: QStylePainter):
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

    def drawSlider_(self, painter):
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

    def drawFrame_(self, painter):
        if self.isEnabled():
            painter.setPen(self.textColor)
        else:
            painter.setPen(QColor(60, 60, 60))

        painter.drawRoundedRect(self.sliderAreaHorizontalOffset, self.sliderAreaTopOffset,
                                self.width() - 2 * self.sliderAreaHorizontalOffset, self.sliderAreaHeight,
                                3, 3)

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

    def paintEvent(self, event):
        opt = QStyleOptionSlider()
        painter = QPainter()
        painter.begin(self)
        painter.setFont(self.font)
        # painter.setRenderHint(QPainter.Antialiasing)
        self.drawFrame_(painter)
        if self.isEnabled():
            self.drawTicks_(painter)
            self.drawSlider_(painter)
            self.drawClips_(painter, opt)
        painter.end()

    # Mouse movement
    def mouseMoveEvent(self, event):
        self.pos = event.pos()
        x = event.pos().x()
        # if mouse is being pressed, update pointer
        if self.clicking and x:
            self.pointerPixelPosition = self.clip(x, self.sliderAreaHorizontalOffset,
                                                  self.width() - self.sliderAreaHorizontalOffset)
            # self.sliderMoved.emit(self.pointerPixelPosition)
        self.update()

    # Mouse pressed
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # x = event.pos().x()
            # self.pointerPixelPosition = self.clip(x, self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            # self.pointerTimePosition = (self.pointerPixelPosition - self.sliderAreaHorizontalOffset) * self.getScale()
            # self.sliderMoved.emit(self.pointerTimePosition)
            # self.update()
            self.clicking = True  # Set clicking check to true

    # Mouse release
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            self.pointerPixelPosition = self.clip(x, self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            self.pointerTimePosition = (self.pointerPixelPosition - self.sliderAreaHorizontalOffset) * self.getScale()
            # print('mousePressEvent::self.pointerTimePosition', self.pointerTimePosition)
            self.sliderMoved.emit(self.pointerTimePosition)
            self.update()
            self.clicking = False  # Set clicking check to false

    # Enter
    def enterEvent(self, event):
        self.is_in = True

    # Leave
    def leaveEvent(self, event):
        self.is_in = False
        self.update()

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
            self.timeline.pointerPixelPosition = round(seconds / self.timeline.getScale() + self.timeline.sliderAreaHorizontalOffset)
            self.timeline.pointerTimePosition = seconds
            self.timeline.update()
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

    def clearRegions(self) -> None:
        pass

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
