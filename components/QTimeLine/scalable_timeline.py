#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from base64 import b64encode

import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint, QLine, QRect, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QKeyEvent, QColor, QFont, QBrush, QPalette, QPen, QPolygon, QPainterPath, QPixmap
from PyQt5.QtWidgets import QStylePainter, QWidget, QLineEdit, QScrollArea, QVBoxLayout, QPushButton, QHBoxLayout, QLabel

from numpy import load

__textColor__ = QColor(187, 187, 187)
__backgroudColor__ = QColor(60, 63, 65)
__font__ = QFont('Decorative', 10)


class VideoSample:
    def __init__(self, duration, color=QColor(180, 180, 180, 180), picture=None, audio=None):
        self.duration = duration
        self.color = color  # Floating color
        self.defColor = color  # DefaultColor
        if picture is not None:
            self.picture = picture.scaledToHeight(45)
        else:
            self.picture = None
        self.startPosition = 0  # Initial position
        self.endPosition = self.duration  # End position


class TimeLine(QWidget):
    positionChanged = pyqtSignal(int)
    selectionChanged = pyqtSignal(VideoSample)

    def __init__(self, duration, length, parent=None):
        super(QWidget, self).__init__()
        self.duration = duration
        self.length = length
        self.parent = parent

        self.sliderAreaHorizontalOffset = 8
        self.sliderAreaTopOffset = 20
        self.sliderAreaHeight = 27
        self.sliderAreaTicksGap = 15
        self.majorTicksHeight = 20
        self.minorTicksHeight = 10
        self.timeLineHeight = 100
        self.theme = 'dark'

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
        self.videoSamples = []  # List of videos samples

        self.setMouseTracking(True)  # Mouse events
        self.setAutoFillBackground(True)  # background

        self.initUI()

    def initUI(self):
        # self.setGeometry(300, 300, self.length, 200)
        self.setFixedWidth(self.length)
        self.setFixedHeight(self.timeLineHeight)

        self.setWindowTitle("Timeline Test")
        # Set Background
        palette = QPalette()
        palette.setColor(QPalette.Background, self.backgroundColor)
        self.setPalette(palette)

    def drawTicksVlt_(self, painter: QStylePainter):
        x = self.sliderAreaHorizontalOffset
        scale = self.getScale()
        for i in range(0, self.width() - 2 * self.sliderAreaHorizontalOffset, 8):
            if i % 5 == 0:
                h, w, z = 25, 1, 10
            else:
                h, w, z = 8, 1, 10
            tickColor = QColor('#8F8F8F' if self.theme == 'dark' else '#444')
            pen = QPen(tickColor)  # , Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            pen.setWidthF(w)
            painter.setPen(pen)

            y = self.rect().top() + self.sliderAreaTopOffset + self.sliderAreaHeight + 8
            painter.drawLine(x, y, x, y + h)
            # if self.parent.mediaAvailable and i % 10 == 0 and (x + 4 + 50) < self.width():
            if i % 10 == 0 and (x + 4 + 60) < self.width():
                painter.setPen(Qt.white if self.theme == 'dark' else Qt.black)
                timecode = self.getTimeString(i * scale, False)
                painter.drawText(x + 4, y + 25, timecode)
            x += 20
            if x > self.width() - self.sliderAreaHorizontalOffset:
                break

    def drawTicks_(self, painter):
        w = 0
        scale = self.getScale()
        while w <= self.width():
            painter.drawText(w - 50, 0, 100, 100, Qt.AlignHCenter, self.getTimeString(w * scale, True))
            w += 100
        # Draw down line
        painter.setPen(QPen(Qt.darkCyan, 5, Qt.SolidLine))
        painter.drawLine(0, 40, self.width(), 40)

        # Draw dash lines
        point = 0
        painter.setPen(QPen(self.textColor))
        painter.drawLine(0, 40, self.width(), 40)
        while point <= self.width():
            if point % 30 != 0:
                painter.drawLine(3 * point, 40, 3 * point, 30)
            else:
                painter.drawLine(3 * point, 40, 3 * point, 20)
            point += 10

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setPen(self.textColor)
        painter.setFont(self.font)
        painter.setRenderHint(QPainter.Antialiasing)

        # self.drawTicks_(painter)
        self.drawTicksVlt_(painter)

        if self.pos is not None and self.is_in:
            x = self.parent.clip(self.pos.x(), self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            painter.drawLine(x, self.sliderAreaTopOffset, x, self.timeLineHeight)

        if self.pointerPixelPosition is not None:
            x = self.pointerPixelPosition
            line = QLine(QPoint(x, 10), QPoint(x, self.height()))
            sliderHandle = QPolygon([QPoint(x - 7, 9), QPoint(x + 7, 9), QPoint(x, 18)])
        else:
            x = self.sliderAreaHorizontalOffset
            line = QLine(QPoint(x, 0), QPoint(x, self.height()))
            sliderHandle = QPolygon([QPoint(x - 7, 9), QPoint(x + 7, 9), QPoint(x, 18)])

        painter.drawRoundedRect(self.sliderAreaHorizontalOffset, self.sliderAreaTopOffset, self.width() - 2 * self.sliderAreaHorizontalOffset, self.sliderAreaHeight, 3, 3)

        # Draw pointer
        painter.setPen(Qt.darkCyan)
        painter.setBrush(QBrush(Qt.darkCyan))

        painter.drawPolygon(sliderHandle)
        painter.drawLine(line)
        painter.end()

    # Mouse movement
    def mouseMoveEvent(self, event):
        self.pos = event.pos()
        x = event.pos().x()
        # if mouse is being pressed, update pointer
        if self.clicking and x:
            self.pointerPixelPosition = self.parent.clip(x, self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            # self.positionChanged.emit(x)
        self.update()

    # Mouse pressed
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            self.pointerPixelPosition = self.parent.clip(x, self.sliderAreaHorizontalOffset, self.width() - self.sliderAreaHorizontalOffset)
            # self.positionChanged.emit(x)
            self.pointerTimePosition = (self.pointerPixelPosition - self.sliderAreaHorizontalOffset) * self.getScale()

            self.update()
            self.clicking = True  # Set clicking check to true

            print('self.pointerTimePos', self.pointerTimePosition)

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


class ScalableTimeLine(QWidget):
    def __init__(self, duration, parent=None):
        super().__init__(parent)
        self.sliderBaseWidth = 770
        self.factor = 1
        self.factorMaximum = 16

        self.timeline = TimeLine(duration, 770, self)
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.timeline)
        self.scrollArea.setContentsMargins(0, 0, 0, 0)
        self.scrollArea.setAlignment(Qt.AlignVCenter)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea.setFixedHeight(self.timeline.timeLineHeight + 16)

        scrollAreaLayout = QVBoxLayout(self)
        scrollAreaLayout.addWidget(self.scrollArea)
        scrollAreaLayout.setContentsMargins(0, 0, 0, 0)

        buttonLayout = QHBoxLayout(self)
        buttonPlus = QPushButton()
        buttonPlus.setText('+')

        buttonMinus = QPushButton()
        buttonMinus.setText('-')

        setValueField = QLineEdit()
        setValueField.setFixedWidth(200)
        setValueField.setText('0.0')
        setValueField.textChanged.connect(self.setValue)

        buttonMaximum = QPushButton()
        buttonMaximum.setText('Max')

        self.label_factor = QLabel()
        self.label_factor.setText('1')
        self.label_factor.setAlignment(Qt.AlignCenter)

        buttonLayout.addWidget(buttonMinus)
        buttonLayout.addWidget(self.label_factor)
        buttonLayout.addWidget(buttonPlus)
        buttonLayout.addWidget(setValueField)

        buttonPlus.clicked.connect(self.toolbarPlus)
        buttonMinus.clicked.connect(self.toolbarMinus)

        scrollAreaLayout.addLayout(buttonLayout)

        self.setLayout(scrollAreaLayout)
        # self.setGeometry(200, 200, 800, 20)
        self.setWindowTitle('Slider Scroll Text')

    def initAttributes(self):
        pass

    def initStyle(self):
        pass

    def clip(self, value, minimum, maximum):
        return minimum if value < minimum else maximum if value > maximum else value

    def toolbarPlus(self):
        if self.factor == 1:
            self.factor += 1
        else:
            self.factor += 2
        self.factor = self.clip(self.factor, 1, self.factorMaximum)
        self.label_factor.setText(str(self.factor))
        self.timeline.setFixedWidth(self.factor * self.sliderBaseWidth)
        # self.slider.setMaximum(self.factor * self.sliderBaseWidth)

    def toolbarMinus(self):
        if self.factor == 2:
            self.factor -= 1
        else:
            self.factor -= 2
        self.factor = self.clip(self.factor, 1, self.factorMaximum)
        self.label_factor.setText(str(self.factor))
        self.timeline.setFixedWidth(self.factor * self.sliderBaseWidth)
        # self.slider.setMaximum(self.factor * self.sliderBaseWidth)

    def value(self):
        return 0

    def setValue(self, seconds: float):
        try:
            seconds = float(seconds)
            self.timeline.pointerPixelPosition = seconds / self.timeline.getScale()
            self.timeline.pointerTimePosition = seconds
            self.timeline.update()
        except ValueError:
            return

    def setRestrictValue(self, value, force=False):
        pass

    def update(self):
        self.timeline.update()

    def clearRegions(self) -> None:
        pass

    def updateProgress(self, region: int = None) -> None:
        pass

    def clearProgress(self):
        pass

    def minimum(self):
        pass

    def maximum(self):
        pass

    def width(self):
        pass

    def setFixedWidth(self, w):
        pass

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Home:
            self.timeline.pointerTimePosition = 0.0
            self.timeline.pointerPixelPosition = self.timeline.sliderAreaHorizontalOffset
            self.timeline.update()
            return

        if event.key() == Qt.Key_End:
            self.timeline.pointerTimePosition = self.timeline.duration
            self.timeline.pointerPixelPosition = self.timeline.width() - self.timeline.sliderAreaHorizontalOffset
            self.timeline.update()
            return


def main():
    app = QApplication(sys.argv)
    scalable_timeline = ScalableTimeLine(2.5)
    scalable_timeline.show()
    app.exec_()


if __name__ == '__main__':
    main()
