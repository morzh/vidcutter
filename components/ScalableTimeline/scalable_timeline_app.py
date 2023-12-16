import sys

from PyQt5.QtCore import Qt, QPoint, QLine, QRect, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QKeyEvent
from PyQt5.QtWidgets import QApplication, QDialog, QStylePainter, QWidget, QLineEdit, QScrollArea, QVBoxLayout, QPushButton, QHBoxLayout, QLabel

from vidcutter.widgets.scalable_timeline_widget import ScalableTimeLine, TimeLine


class ScalableTimeLineWindow(QWidget):
    def __init__(self, duration, parent=None):
        super().__init__(parent)
        self.factor = 1
        self.factorMaximum = 16
        self.mediaAvailable = True
        self.sliderBaseWidth = 770

        self.timeline = ScalableTimeLine(self)
        scrollAreaLayout = QVBoxLayout(self)
        scrollAreaLayout.addWidget(self.timeline)
        # scrollAreaLayout.setContentsMargins(0, 0, 0, 0)

        buttonLayout = QHBoxLayout(self)
        buttonPlus = QPushButton()
        buttonPlus.setText('+')

        buttonMinus = QPushButton()
        buttonMinus.setText('-')

        setValueField = QLineEdit()
        setValueField.setFixedWidth(200)
        setValueField.setText('0.0')
        setValueField.textChanged.connect(self.timeline.setValue)

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

    def initAttributes(self):
        pass

    def initStyle(self):
        pass

    def toolbarPlus(self):
        if self.factor == 1:
            self.factor += 1
        else:
            self.factor += 2
        self.factor = TimeLine.clip(self.factor, 1, self.factorMaximum)
        self.label_factor.setText(str(self.factor))
        self.timeline.timeline.setFixedWidth(self.factor * self.sliderBaseWidth)

    def toolbarMinus(self):
        if self.factor == 2:
            self.factor -= 1
        else:
            self.factor -= 2
        self.factor = TimeLine.clip(self.factor, 1, self.factorMaximum)
        self.label_factor.setText(str(self.factor))
        self.timeline.timeline.setFixedWidth(self.factor * self.sliderBaseWidth)

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

    def setFixedWidth(self, w):
        super().setFixedWidth(w + 36)
        self.timeline.setFixedWidth(w)

def main():
    app = QApplication(sys.argv)
    scalable_timeline = ScalableTimeLineWindow(12.5)
    scalable_timeline.timeline.setFixedWidth(800)
    scalable_timeline.timeline.timeline.duration = 15.5
    # scalable_timeline.setFixedHeight(102)
    # scalable_timeline.timeline.setFixedHeight(132)
    scalable_timeline.setEnabled(True)
    scalable_timeline.show()
    app.exec_()


if __name__ == '__main__':
    main()
