#!/usr/bin/python

import sys

from PyQt5.QtCore import (QDir)
from PyQt5.QtWidgets import (QWidget, QMessageBox, QApplication, QVBoxLayout, QPushButton, QFileDialog)
from vidcutter.data_structures.video_list import VideoList
from vidcutter.widgets.video_list_widget import VideoListWidget


class VideosList(QWidget):
    timeformat = 'hh:mm:ss.zzz'
    theme = 'light'

    def __init__(self):
        super().__init__()

        self.videoList = None
        self.listWidget = VideoListWidget(parent=self)
        self.listWidget.itemDoubleClicked.connect(self.onClicked)

        self.initUI()

    def initUI(self):
        vbox = QVBoxLayout(self)
        open_button = QPushButton(self)
        open_button.setText('Open')
        open_button.clicked.connect(self.openFolder)
        vbox.addWidget(self.listWidget)
        vbox.addWidget(open_button)
        self.setLayout(vbox)

        self.setGeometry(300, 300, 200, 750)
        self.setWindowTitle('QListWidget')
        self.show()

    def openFolder(self):
        outputFolder = QFileDialog.getExistingDirectory(caption='Select Folder', directory=QDir.currentPath())
        self.videoList = VideoList(outputFolder, 'data.pickle')
        self.listWidget.renderList(self.videoList)

    def onClicked(self, item):
        QMessageBox.information(self, "Info", item.text())


def main():
    app = QApplication(sys.argv)
    ex = VideosList()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
