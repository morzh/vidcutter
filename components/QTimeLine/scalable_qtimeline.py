#!/usr/bin/python3
# -*- coding: utf-8 -*-
import tempfile
from base64 import b64encode

import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint, QLine, QRect, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QPalette, QPen, QPolygon, QPainterPath, QPixmap
from PyQt5.QtWidgets import QWidget, QLineEdit, QScrollArea, QVBoxLayout, QPushButton, QHBoxLayout, QLabel

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
        self.startPos = 0  # Inicial position
        self.endPos = self.duration  # End position


class QTimeLine(QWidget):
    positionChanged = pyqtSignal(int)
    selectionChanged = pyqtSignal(VideoSample)

    def __init__(self, duration, length, parent=None):
        super(QWidget, self).__init__()
        self.duration = duration
        self.length = length
        self.parent = parent

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
        self.setGeometry(300, 300, self.length, 200)
        self.setWindowTitle("Timeline Test")
        # Set Background
        pal = QPalette()
        pal.setColor(QPalette.Background, self.backgroundColor)
        self.setPalette(pal)

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setPen(self.textColor)
        painter.setFont(self.font)
        painter.setRenderHint(QPainter.Antialiasing)
        w = 0
        # Draw time
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

        if self.pos is not None and self.is_in:
            painter.drawLine(self.pos.x(), 0, self.pos.x(), 40)

        if self.pointerPos is not None:
            x = int(self.parent.clip(self.pointerTimePos, 0, self.duration)/self.getScale())
            line = QLine(QPoint(x, 40), QPoint(x, self.height()))
            poly = QPolygon([QPoint(x - 10, 20),
                             QPoint(x + 10, 20),
                             QPoint(x, 40)])
        else:
            line = QLine(QPoint(0, 0), QPoint(0, self.height()))
            poly = QPolygon([QPoint(-10, 20), QPoint(10, 20), QPoint(0, 40)])

        # Draw samples
        t = 0
        for sample in self.videoSamples:
            # Clear clip path
            path = QPainterPath()
            path.addRoundedRect(QRectF(t / scale, 50, sample.duration / scale, 200), 10, 10)
            painter.setClipPath(path)

            # Draw sample
            path = QPainterPath()
            painter.setPen(sample.color)
            path.addRoundedRect(QRectF(t/scale, 50, sample.duration/scale, 50), 10, 10)
            sample.startPos = t/scale
            sample.endPos = t/scale + sample.duration/scale
            painter.fillPath(path, sample.color)
            painter.drawPath(path)

            # Draw preview pictures
            if sample.picture is not None:
                if sample.picture.size().width() < sample.duration/scale:
                    path = QPainterPath()
                    path.addRoundedRect(QRectF(t/scale, 52.5, sample.picture.size().width(), 45), 10, 10)
                    painter.setClipPath(path)
                    painter.drawPixmap(QRect(t/scale, 52.5, sample.picture.size().width(), 45), sample.picture)
                else:
                    path = QPainterPath()
                    path.addRoundedRect(QRectF(t / scale, 52.5, sample.duration/scale, 45), 10, 10)
                    painter.setClipPath(path)
                    pic = sample.picture.copy(0, 0, sample.duration/scale, 45)
                    painter.drawPixmap(QRect(t / scale, 52.5, sample.duration/scale, 45), pic)
            t += sample.duration

        # Clear clip path
        path = QPainterPath()
        path.addRect(self.rect().x(), self.rect().y(), self.rect().width(), self.rect().height())
        painter.setClipPath(path)

        # Draw pointer
        painter.setPen(Qt.darkCyan)
        painter.setBrush(QBrush(Qt.darkCyan))

        painter.drawPolygon(poly)
        painter.drawLine(line)
        painter.end()

    # Mouse movement
    def mouseMoveEvent(self, event):
        self.pos = event.pos()

        # if mouse is being pressed, update pointer
        if self.clicking:
            x = self.pos.x()
            self.pointerPos = x
            self.positionChanged.emit(x)
            self.checkSelection(x)
            self.pointerTimePos = self.pointerPos*self.getScale()

        self.update()

    # Mouse pressed
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            self.pointerPos = x
            self.positionChanged.emit(x)
            self.pointerTimePos = self.pointerPos * self.getScale()

            self.checkSelection(x)

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
            if sample.startPos < x < sample.endPos:
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
        return float(self.duration)/float(self.width())

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


class ScalableQtimeLine(QWidget):
    def __init__(self, duration, parent=None):
        super().__init__(parent)
        self.sliderBaseWidth = 770
        self.factor = 1
        self.factor_maximum = 16

        self.timeline = QTimeLine(duration, 770, self)
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.timeline)
        self.scrollArea.setAlignment(Qt.AlignVCenter)

        scrollAreaLayout = QVBoxLayout(self)
        scrollAreaLayout.addWidget(self.scrollArea)

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
        self.setGeometry(200, 200, 800, 20)
        self.setWindowTitle('Slider Scroll Text')

    def clip(self, value, minimum, maximum):
        return minimum if value < minimum else maximum if value > maximum else value

    def toolbarPlus(self):
        if self.factor == 1:
            self.factor += 1
        else:
            self.factor += 2
        self.factor = self.clip(self.factor, 1, self.factor_maximum)
        self.label_factor.setText(str(self.factor))
        self.timeline.setFixedWidth(self.factor * self.sliderBaseWidth)
        # self.slider.setMaximum(self.factor * self.sliderBaseWidth)

    def toolbarMinus(self):
        if self.factor == 2:
            self.factor -= 1
        else:
            self.factor -= 2
        self.factor = self.clip(self.factor, 1, self.factor_maximum)
        self.label_factor.setText(str(self.factor))
        self.timeline.setFixedWidth(self.factor * self.sliderBaseWidth)
        # self.slider.setMaximum(self.factor * self.sliderBaseWidth)

    def setValue(self, seconds: float):
        try:
            seconds = float(seconds)
            self.timeline.pointerPos = seconds / self.timeline.getScale()
            self.timeline.pointerTimePos = seconds
            self.timeline.update()
        except ValueError:
            return


def main():
    app = QApplication(sys.argv)
    scalable_timeline = ScalableQtimeLine(2.5)
    scalable_timeline.show()
    app.exec_()


if __name__ == '__main__':
    main()

