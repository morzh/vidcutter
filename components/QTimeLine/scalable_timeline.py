#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from base64 import b64encode

import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint, QLine, QRect, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QPalette, QPen, QPolygon, QPainterPath, QPixmap
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

        # Set variables
        self.backgroundColor = __backgroudColor__
        self.textColor = __textColor__
        self.font = __font__
        self.pos = None
        self.pointerPos = None
        self.pointerTimePos = None
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

    def drawTicks_(self, painter):
        w = 0
        scale = self.getScale()
        while w <= self.width():
            painter.drawText(w - 50, 0, 100, 100, Qt.AlignHCenter, self.getTimeString(w * scale))
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

        if self.pos is not None and self.is_in:
            x = self.pos.x()
            x = self.parent.clip(x, self.sliderAreaHorizontalOffset, self.width() - 2 * self.sliderAreaHorizontalOffset)
            painter.drawLine(x, self.sliderAreaTopOffset, x, self.timeLineHeight)

        if self.pointerPos is not None:
            x = self.sliderAreaHorizontalOffset + int(self.parent.clip(self.pointerTimePos, 0, self.duration) / self.getScale())
            line = QLine(QPoint(x, 10), QPoint(x, self.height()))
            sliderHandle = QPolygon([QPoint(x - 7, 8), QPoint(x + 7, 8), QPoint(x, 17)])
        else:
            shift = self.sliderAreaHorizontalOffset
            line = QLine(QPoint(shift, 0), QPoint(shift, self.height()))
            sliderHandle = QPolygon([QPoint(shift - 7, 10), QPoint(shift + 7, 10), QPoint(shift, 20)])

        # Draw samples

        # Clear clip path
        # path = QPainterPath()
        # path.addRect(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height())
        # painter.setClipPath(path)

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

        # if mouse is being pressed, update pointer
        if self.clicking and self.pos.x():
            x = self.pos.x()
            # x = self.parent.clip(x, self.sliderAreaHorizontalOffset, self.width() - 2 * self.sliderAreaHorizontalOffset)
            self.pointerPos = x - self.sliderAreaHorizontalOffset
            self.positionChanged.emit(x)
            # self.checkSelection(x)
            self.pointerTimePos = self.pointerPos * self.getScale()

        self.update()

    # Mouse pressed
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            # x = self.parent.clip(x, self.sliderAreaHorizontalOffset, self.width() - 2 * self.sliderAreaHorizontalOffset)
            self.pointerPos = x - self.sliderAreaHorizontalOffset
            self.positionChanged.emit(x)
            self.pointerTimePos = self.pointerPos * self.getScale()

            # self.checkSelection(x)

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

    # check selection
    def checkSelection(self, x):
        # Check if user clicked in video sample
        for sample in self.videoSamples:
            if sample.startPosition < x < sample.endPosition:
                sample.color = Qt.darkCyan
                if self.selectedSample is not sample:
                    self.selectedSample = sample
                    self.selectionChanged.emit(sample)
            else:
                sample.color = sample.defColor

    # Get time string from seconds
    def getTimeString(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%02d:%02d:%02d" % (h, m, s)


    # Get scale from length
    def getScale(self):
        return float(self.duration)/float(self.width() - 2 * self.sliderAreaHorizontalOffset)

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
            self.timeline.pointerPos = seconds / self.timeline.getScale()
            self.timeline.pointerTimePos = seconds
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




def main():
    app = QApplication(sys.argv)
    scalable_timeline = ScalableTimeLine(2.5)
    scalable_timeline.show()
    app.exec_()


if __name__ == '__main__':
    main()

