import os
from PyQt5 import QtCore, QtGui, QtWidgets, QtMultimedia, QtMultimediaWidgets
from PyQt5.Qt import *


class GraphicsPixmapButton(QGraphicsPixmapItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def mousePressEvent(self, event):
        print('Mouse Click')


class GraphicsPixmapItem(QGraphicsPixmapItem):
    def __init__(self, parent=None):
        super(GraphicsPixmapItem, self).__init__(parent)

    def mousePressEvent(self, event):
        print(f'QGraphicsPixmapItem: {event.pos()}')
        super().mousePressEvent(event)


class Widget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Widget, self).__init__(parent)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.gv = QtWidgets.QGraphicsView(self.scene)

        self.videoitem = QtMultimediaWidgets.QGraphicsVideoItem()
        self.videoitem.setSize(QSizeF(640, 480))
        self.scene.addItem(self.videoitem)

        self.pic = GraphicsPixmapButton(self.videoitem)
        self.pic.setPixmap(QPixmap('ok.png').scaled(40, 40))
        # self.pic.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.pic.setOffset(20, 20)

        self.text = QGraphicsTextItem(self.videoitem)
        self.text.setHtml('<h1>Hello PyQt5</h1>')
        self.text.setDefaultTextColor(QColor(66, 222, 88))
        self.text.setPos(100, 380)

        # self.button = QPushButton(self.videoitem)
        # self.button.setText('asdas')
        # self.button.move(50, 150)

        self._player = QtMultimedia.QMediaPlayer(self, QtMultimedia.QMediaPlayer.VideoSurface)
        self._player.stateChanged.connect(self.on_stateChanged)
        self._player.setVideoOutput(self.videoitem)

        # ----------- установите свое ------------------------> vvvvvvvvvvvvvvvvv <--------
        file = os.path.join(os.path.dirname(__file__), "file_example_AVI_1280_1_5MG_.avi")
        print(file)

        self._player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(file)))
        button = QtWidgets.QPushButton("Play")
        button.clicked.connect(self._player.play)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.gv)
        lay.addWidget(button)

    @QtCore.pyqtSlot(QtMultimedia.QMediaPlayer.State)
    def on_stateChanged(self, state):
        if state == QtMultimedia.QMediaPlayer.PlayingState:
            self.gv.fitInView(self.videoitem, QtCore.Qt.KeepAspectRatio)


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    w = Widget()
    w.resize(670, 540)
    w.show()
    sys.exit(app.exec_())
