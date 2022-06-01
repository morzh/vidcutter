#!-*- coding:utf-8 -*-
import os
import sys

from PyQt5 import uic
from PyQt5.QtCore import Qt, QRect, QSettings
from PyQt5.QtWidgets import QDialog, QApplication, QListWidgetItem, QScrollArea

from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize,
                          Qt, QTime, QTimer, QUrl)
from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtWidgets import (QAction, qApp, QApplication, QDialog, QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
                             QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy, QStyleFactory,
                             QVBoxLayout, QWidget, QScrollBar, QSlider)
from vidcutter.VideoSliderTest import VideoSliderTest, VideoSliderScaleContainer

class ContainerVideoSlider(QWidget):
    def __init__(self, parent: QMainWindow):
        super(ContainerVideoSlider, self).__init__()
        self.init_settings()
        # self.parent = parent
        self.mediaAvailable = False
        self.slider = VideoSliderTest(self)
        self.thumbnailsButton = QPushButton(self, flat=True, checkable=True, objectName='thumbnailsButton', statusTip='Toggle timeline thumbnails',
                                            cursor=Qt.PointingHandCursor, toolTip='Toggle thumbnails')

    def init_settings(self) -> None:
        try:
            settings_path = self.get_app_config_path()
        except AttributeError:
            if sys.platform == 'win32':
                settings_path = os.path.join(QDir.homePath(), 'AppData', 'Local', qApp.applicationName().lower())
            elif sys.platform == 'darwin':
                settings_path = os.path.join(QDir.homePath(), 'Library', 'Preferences',
                                             qApp.applicationName().lower())
            else:
                settings_path = os.path.join(QDir.homePath(), '.config', qApp.applicationName().lower())
        os.makedirs(settings_path, exist_ok=True)
        settings_file = '{}.ini'.format(qApp.applicationName().lower())
        self.settings = QSettings(os.path.join(settings_path, settings_file), QSettings.IniFormat)
        if self.settings.value('geometry') is not None:
            self.restoreGeometry(self.settings.value('geometry'))
        if self.settings.value('windowState') is not None:
            self.restoreState(self.settings.value('windowState'))
        self.theme = self.settings.value('theme', 'light', type=str)
        self.startupvol = self.settings.value('volume', 100, type=int)
        self.verboseLogs = self.settings.value('verboseLogs', 'off', type=str) in {'on', 'true'}

def main():
   app = QApplication(sys.argv)
   dialog = ContainerVideoSlider(QMainWindow)
   dialog.show()
   app.exec_()


if __name__ == '__main__':
   main()