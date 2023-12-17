#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from base64 import b64encode

import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint, QLine, QRect, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QKeyEvent, QColor, QFont, QBrush, QPalette, QPen, QPolygon, QPainterPath, QPixmap
from PyQt5.QtWidgets import QDialog, QStylePainter, QWidget, QLineEdit, QScrollArea, QVBoxLayout, QPushButton, QHBoxLayout, QLabel

from numpy import load

__textColor__ = QColor(187, 187, 187)
__backgroudColor__ = QColor(60, 63, 65)
__font__ = QFont('Decorative', 10)


class TimeLine(QWidget):
    sliderMoved = pyqtSignal(int)

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
        self.theme = 'dark'
        self.setObjectName('videoslider')

        # Set variables
        self.backgroundColor = __backgroudColor__
        self.textColor = __textColor__
        self.font = __font__
        self.pos = None
        self.pointerPixelPosition = None
        self.pointerTimePosition = None
        self.selectedSample = None
        self.clicking = False  # Check if mouse left button is being pressed
        self.is_in = False  # check if user is in the widget

        self.setMouseTracking(True)  # Mouse events
        self.setAutoFillBackground(True)  # background

        self.initAttributes()

    def initAttributes(self):
        # self.setGeometry(300, 300, self.length, 200)
        self.setFixedWidth(self.length)
        self.setFixedHeight(self.timeLineHeight)

        # self.setWindowTitle("Timeline Test")
        # Set Background
        palette = QPalette()
        palette.setColor(QPalette.Background, self.backgroundColor)
        self.setPalette(palette)

    def drawTicks_(self, painter: QStylePainter):
        scale = self.getScale()
        y = self.rect().top() + self.sliderAreaTopOffset + self.sliderAreaHeight + 8
        tickStep = 20
        timeTickStep = tickStep * 5
        millisecondsFlag = True if self.getTimeString(0) == self.getTimeString(timeTickStep * scale) else False

        for i in range(0, self.width() - 2 * self.sliderAreaHorizontalOffset, tickStep):
            x = i + self.sliderAreaHorizontalOffset
            if i % timeTickStep == 0:
                h, w, z = 30, 1, 10
                if i < self.width() - (tickStep * 5):
                    painter.setPen(Qt.white if self.theme == 'dark' else Qt.black)
                    timecode = self.getTimeString(i * scale, millisecondsFlag)
                    painter.drawText(x + 5, y + 25, timecode)
            else:
                h, w, z = 8, 1, 10

            tickColor = QColor('#8F8F8F' if self.theme == 'dark' else '#444')
            pen = QPen(tickColor)  # , Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            pen.setWidthF(w)
            painter.setPen(pen)
            painter.drawLine(x, y, x, y + h)

    def drawSlider_(self, painter):
        if self.pos is not None and self.is_in:
            x = self.clip(self.pos.x(), self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            painter.drawLine(x, self.sliderAreaTopOffset, x, self.timeLineHeight)

        if self.pointerPixelPosition is not None:
            x = int(self.pointerPixelPosition)
            y = self.sliderAreaTopOffset -1
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

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setPen(self.textColor)
        painter.setFont(self.font)
        # painter.setRenderHint(QPainter.Antialiasing)

        painter.drawRoundedRect(self.sliderAreaHorizontalOffset, self.sliderAreaTopOffset,
                                self.width() - 2 * self.sliderAreaHorizontalOffset, self.sliderAreaHeight,
                                3, 3)

        if self.isEnabled():
            self.drawTicks_(painter)
            self.drawSlider_(painter)
        painter.end()

    # Mouse movement
    def mouseMoveEvent(self, event):
        self.pos = event.pos()
        x = event.pos().x()
        # if mouse is being pressed, update pointer
        if self.clicking and x:
            self.pointerPixelPosition = self.clip(x, self.sliderAreaHorizontalOffset,
                                                  self.width() - self.sliderAreaHorizontalOffset)
            self.sliderMoved.emit(self.pointerPixelPosition)
        self.update()

    # Mouse pressed
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            self.pointerPixelPosition = self.clip(x, self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            self.pointerTimePosition = (self.pointerPixelPosition - self.sliderAreaHorizontalOffset) * self.getScale()
            self.sliderMoved.emit(self.pointerPixelPosition)
            self.update()
            self.clicking = True  # Set clicking check to true

    # Mouse release
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
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
    def getScale(self):
        return float(self.duration) / float(self.width() - 2 * self.sliderAreaHorizontalOffset)

    # Get duration
    def getDuration(self):
        return self.duration

    # Get selected sample
    def getSelectedSample(self):
        return self.selectedSample

    # Set background color
    def setBackgroundColor(self, color):
        self.backgroundColor = color

    # Set text color
    def setTextColor(self, color):
        self.textColor = color

    # Set Font
    def setTextFont(self, font):
        self.font = font


class ScalableTimeLine(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.restrictValue = 0

        self.timeline = TimeLine(self)
        self.setWidget(self.timeline)
        self.setAlignment(Qt.AlignVCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def initAttributes(self):
        self.setEnabled(False)
        self.timeline.setEnabled(False)

    def value(self):
        return self.timeline.pointerTimePosition

    def setRange(self, start, end):
        self.timeline.duration = end

    def setValue(self, seconds: int):
        try:
            seconds = float(seconds)
            self.timeline.pointerPixelPosition = round(seconds / self.timeline.getScale() + self.timeline.sliderAreaHorizontalOffset)
            self.timeline.pointerTimePosition = seconds
            self.timeline.update()
        except ValueError('seconds should be in float number format'):
            return

    def setEnabled(self, flag):
        self.timeline.setEnabled(flag)
        super().setEnabled(flag)

    def setRestrictValue(self, value, force=False):
        self.restrictValue = value

    def update(self):
        self.timeline.update()

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

    def width(self):
        return self.width()

    def setFixedWidth(self, width):
        super().setFixedWidth(width)
        self.timeline.setFixedWidth(width - 2)

    def setFixedHeight(self, height):
        super().setFixedHeight(height)
        self.timeline.setFixedHeight(height - 16)

