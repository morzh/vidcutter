#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# VidCutter - media cutter & joiner
#
# copyright © 2018 Pete Alexandrou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#######################################################################

import logging
import os
import re
import sys
import time
import pickle
import shutil
from datetime import timedelta
from functools import partial
from typing import Callable, List, Optional, Union

from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize,
                          Qt, QTime, QTimer, QUrl)
from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtWidgets import (QAction, qApp, QApplication, QDialog, QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
                             QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy, QStyleFactory,
                             QVBoxLayout, QWidget)

import sip

# noinspection PyUnresolvedReferences
from vidcutter import resources
from vidcutter.dialogs.about import About
from vidcutter.dialogs.changelog import Changelog
from vidcutter.dialogs.mediainfo import MediaInfo
from vidcutter.mediastream import StreamSelector
from vidcutter.dialogs.settings import SettingsDialog
from vidcutter.dialogs.updater import Updater
from vidcutter.VideoClipsListWidget import VideoClipsListWidget
from vidcutter.VideoSlider import VideoSlider
from vidcutter.VideoSliderWidget import VideoSliderWidget
from vidcutter.VideoStyle import VideoStyleDark, VideoStyleLight

from vidcutter.libs.config import Config, InvalidMediaException, VideoFilter
from vidcutter.libs.mpvwidget import mpvWidget
from vidcutter.libs.notifications import JobCompleteNotification
from vidcutter.libs.taskbarprogress import TaskbarProgress
from vidcutter.libs.videoservice import VideoService
from vidcutter.libs.widgets import (VCBlinkText, VCDoubleInputDialog, VCFilterMenuAction, VCFrameCounter, VCChapterInputDialog, VCMessageBox, VCProgressDialog, VCTimeCounter,
                                    VCToolBarButton, VCVolumeSlider, VCConfirmDialog)

from vidcutter.VideoItemClip import VideoItemClip

from vidcutter.VideoList import VideoList
from vidcutter.VideoListWidget import VideoListWidget
from vidcutter.QPixmapPickle import QPixmapPickle
from vidcutter.dialogs.VideoDescriptionDialog import VideoDescriptionDialog


class VideoCutter(QWidget):
    errorOccurred = pyqtSignal(str)
    timeformat = 'hh:mm:ss.zzz'
    runtimeformat = 'hh:mm:ss'

    def __init__(self, parent: QMainWindow):
        super(VideoCutter, self).__init__(parent)
        self.setObjectName('videocutter')
        self.logger = logging.getLogger(__name__)
        self.parent = parent
        self.theme = self.parent.theme
        self.workFolder = self.parent.WORKING_FOLDER
        self.settings = self.parent.settings
        self.filter_settings = Config.filter_settings()
        self.currentMedia, self.mediaAvailable, self.mpvError = None, False, False
        self.currentMediaPreview = None
        self.projectDirty, self.projectSaved, self.debugonstart = False, False, False
        self.smartcut_monitor, self.notify = None, None
        self.fonts = []
        self._dataFolder = ''
        self._dataFilename = 'data.pickle'
        self._dataFilenameTemp = 'data.pickle.tmp'
        self.previewPostfix = '.preview.mp4'
        self.folderOpened = False

        self.initTheme()
        self.updater = Updater(self.parent)

        self.videoSlider = VideoSlider(self)
        self.videoSlider.setEnabled(False)
        self.videoSlider.setTracking(True)
        self.videoSlider.setMouseTracking(True)
        self.videoSlider.setUpdatesEnabled(False)
        self.videoSlider.sliderMoved.connect(self.setPosition)

        self.sliderWidget = VideoSliderWidget(self, self.videoSlider)
        self.sliderWidget.setLoader(True)
        self.sliderWidget.setMouseTracking(False)

        self.taskbar = TaskbarProgress(self.parent)


        self.videoList = None
        self.videoListWidget = VideoListWidget(parent=self)
        self.videoListWidget.itemDoubleClicked.connect(self.loadMedia)
        self.videoListWidget.itemClicked.connect(self.editVideoDescription)

        # self.videos = []
        # self.videoList.currentVideoIndex = 0
        # self.clipTimes = []
        self.inCut, self.newproject = False, False
        self.finalFilename = ''
        self.totalRuntime, self.frameRate = 0, 0
        self.notifyInterval = 1000

        self.createChapters = self.settings.value('chapters', 'on', type=str) in {'on', 'true'}
        self.enableOSD = self.settings.value('enableOSD', 'on', type=str) in {'on', 'true'}
        self.hardwareDecoding = self.settings.value('hwdec', 'on', type=str) in {'on', 'auto'}
        self.enablePBO = self.settings.value('enablePBO', 'off', type=str) in {'on', 'true'}
        self.keepRatio = self.settings.value('aspectRatio', 'keep', type=str) == 'keep'
        self.keepClips = self.settings.value('keepClips', 'off', type=str) in {'on', 'true'}
        self.nativeDialogs = self.settings.value('nativeDialogs', 'on', type=str) in {'on', 'true'}
        self.indexLayout = self.settings.value('indexLayout', 'right', type=str)
        self.timelineThumbs = self.settings.value('timelineThumbs', 'on', type=str) in {'on', 'true'}
        self.showConsole = self.settings.value('showConsole', 'off', type=str) in {'on', 'true'}
        self.smartcut = self.settings.value('smartcut', 'off', type=str) in {'on', 'true'}
        self.level1Seek = self.settings.value('level1Seek', 2, type=float)
        self.level2Seek = self.settings.value('level2Seek', 5, type=float)
        self.verboseLogs = self.parent.verboseLogs
        self.lastFolder = self.settings.value('lastFolder', QDir.homePath(), type=str)

        self.videoService = VideoService(self.settings, self)
        self.videoService.progress.connect(self.videoSlider.updateProgress)
        # self.videoService.finished.connect(self.smartmonitor)
        self.videoService.error.connect(self.completeOnError)
        self.videoService.addScenes.connect(self.addScenes)

        self._initIcons()
        self._initActions()

        self.appmenu = QMenu(self.parent)
        self.help_menu = QMenu('Help n Logs', self.appmenu)
        self.clipindex_removemenu = QMenu(self)
        self._initMenus()
        self._initNoVideo()

        self.cliplist = VideoClipsListWidget(self)
        self.cliplist.clicked.connect(self.videoListSingleClick)
        self.cliplist.doubleClicked.connect(self.videoListDoubleClick)
        self.cliplist.customContextMenuRequested.connect(self.itemMenu)
        self.cliplist.itemChanged.connect(self.videosVisibility)
        self.cliplist.model().rowsInserted.connect(self.setProjectDirty)
        self.cliplist.model().rowsRemoved.connect(self.setProjectDirty)
        self.cliplist.model().rowsMoved.connect(self.setProjectDirty)
        self.cliplist.model().rowsMoved.connect(self.syncClipList)

        self.clipindex_move_up = QPushButton(self)
        self.clipindex_move_up.setObjectName('clip_move_up')
        self.clipindex_move_up.clicked.connect(self.moveItemUp)
        self.clipindex_move_up.setToolTip('Move clip up')
        self.clipindex_move_up.setStatusTip('Moves clip one row up')
        self.clipindex_move_up.setCursor(Qt.PointingHandCursor)
        self.clipindex_move_up.setEnabled(False)

        self.clipindex_move_down = QPushButton(self)
        self.clipindex_move_down.setObjectName('clip_move_down')
        self.clipindex_move_down.clicked.connect(self.moveItemDown)
        self.clipindex_move_down.setToolTip('Move clip down')
        self.clipindex_move_down.setStatusTip('Moves clip one row down')
        self.clipindex_move_down.setCursor(Qt.PointingHandCursor)
        self.clipindex_move_down.setEnabled(False)

        self.clipindex_clips_remove = QPushButton(self)
        self.clipindex_clips_remove.setObjectName('clipremove')
        self.clipindex_clips_remove.setToolTip('Remove clips')
        self.clipindex_clips_remove.setStatusTip('Remove clips from your index')
        self.clipindex_clips_remove.setLayoutDirection(Qt.RightToLeft)
        self.clipindex_clips_remove.setMenu(self.clipindex_removemenu)
        self.clipindex_clips_remove.setCursor(Qt.PointingHandCursor)
        self.clipindex_clips_remove.setEnabled(False)

        if sys.platform in {'win', 'darwin'}:
            self.clipindex_move_up.setStyle(QStyleFactory.create('Fusion'))
            self.clipindex_move_down.setStyle(QStyleFactory.create('Fusion'))
            self.clipindex_clips_remove.setStyle(QStyleFactory.create('Fusion'))

        clipindex_layout = QHBoxLayout()
        clipindex_layout.setSpacing(1)
        clipindex_layout.setContentsMargins(0, 0, 0, 0)
        clipindex_layout.addWidget(self.clipindex_move_up)
        clipindex_layout.addWidget(self.clipindex_move_down)
        clipindex_layout.addSpacing(15)
        clipindex_layout.addWidget(self.clipindex_clips_remove)

        clipindexTools = QWidget(self)
        clipindexTools.setObjectName('clipindextools')
        clipindexTools.setLayout(clipindex_layout)

        self.clipIndexLayout = QVBoxLayout()
        self.clipIndexLayout.setSpacing(0)
        self.clipIndexLayout.setContentsMargins(0, 0, 0, 0)
        self.clipIndexLayout.addWidget(self.cliplist)
        self.clipIndexLayout.addSpacing(3)
        self.clipIndexLayout.addWidget(clipindexTools)

        self.videoLayout = QHBoxLayout()
        self.videoLayout.setContentsMargins(0, 0, 0, 0)

        self.videoLayout.addWidget(self.videoListWidget)
        self.videoLayout.addSpacing(10)
        self.videoLayout.addWidget(self.novideoWidget)
        self.videoLayout.addSpacing(10)
        self.videoLayout.addLayout(self.clipIndexLayout)

        self.timeCounter = VCTimeCounter(self)
        self.timeCounter.timeChanged.connect(lambda newtime: self.setPosition(newtime.msecsSinceStartOfDay()))
        self.frameCounter = VCFrameCounter(self)
        self.frameCounter.setReadOnly(True)

        countersLayout = QHBoxLayout()
        countersLayout.setContentsMargins(0, 0, 0, 0)
        countersLayout.addStretch(1)
        # noinspection PyArgumentList
        countersLayout.addWidget(QLabel('TIME:', objectName='tcLabel'))
        countersLayout.addWidget(self.timeCounter)
        countersLayout.addStretch(1)
        # noinspection PyArgumentList
        countersLayout.addWidget(QLabel('FRAME:', objectName='fcLabel'))
        countersLayout.addWidget(self.frameCounter)
        countersLayout.addStretch(1)

        countersWidget = QWidget(self)
        countersWidget.setObjectName('counterwidgets')
        countersWidget.setContentsMargins(0, 0, 0, 0)
        countersWidget.setLayout(countersLayout)
        countersWidget.setMaximumHeight(28)

        self.mpvWidget = self.getMPV(self)
        self.clipIsPlaying = False
        self.clipIsPlayingIndex = -1

        self.videoplayerLayout = QVBoxLayout()
        self.videoplayerLayout.setSpacing(0)
        self.videoplayerLayout.setContentsMargins(0, 0, 0, 0)
        self.videoplayerLayout.addWidget(self.mpvWidget)
        self.videoplayerLayout.addWidget(countersWidget)

        self.videoplayerWidget = QFrame(self)
        self.videoplayerWidget.setObjectName('videoplayer')
        self.videoplayerWidget.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.videoplayerWidget.setLineWidth(0)
        self.videoplayerWidget.setMidLineWidth(0)
        self.videoplayerWidget.setVisible(False)
        self.videoplayerWidget.setLayout(self.videoplayerLayout)

        # noinspection PyArgumentList
        self.thumbnailsButton = QPushButton(self, flat=True, checkable=True, objectName='thumbnailsButton',  statusTip='Toggle timeline thumbnails', cursor=Qt.PointingHandCursor, toolTip='Toggle thumbnails')
        self.thumbnailsButton.setFixedSize(32, 29 if self.theme == 'dark' else 31)
        self.thumbnailsButton.setChecked(self.timelineThumbs)
        self.thumbnailsButton.toggled.connect(self.toggleThumbs)
        if self.timelineThumbs:
            self.videoSlider.setObjectName('nothumbs')

        # noinspection PyArgumentList
        self.osdButton = QPushButton(self, flat=True, checkable=True, objectName='osdButton', toolTip='Toggle OSD', statusTip='Toggle on-screen display', cursor=Qt.PointingHandCursor)
        self.osdButton.setFixedSize(31, 29 if self.theme == 'dark' else 31)
        self.osdButton.setChecked(self.enableOSD)
        self.osdButton.toggled.connect(self.toggleOSD)

        if self.showConsole:
            self.mpvWidget.setLogLevel('v')
            os.environ['DEBUG'] = '1'
            self.parent.console.show()

        # noinspection PyArgumentList
        self.muteButton = QPushButton(objectName='muteButton', icon=self.unmuteIcon, flat=True, toolTip='Mute', statusTip='Toggle audio mute', iconSize=QSize(16, 16), clicked=self.muteAudio,
                                      cursor=Qt.PointingHandCursor)
        # noinspection PyArgumentList
        self.volSlider = VCVolumeSlider(orientation=Qt.Horizontal, toolTip='Volume', statusTip='Adjust volume level', cursor=Qt.PointingHandCursor, value=self.parent.startupvol, minimum=0,
                                        maximum=130, minimumHeight=22, sliderMoved=self.setVolume)
        # noinspection PyArgumentList
        self.fullscreenButton = QPushButton(objectName='fullscreenButton', icon=self.fullscreenIcon, flat=True, toolTip='Toggle fullscreen', statusTip='Switch to fullscreen video',
                                            iconSize=QSize(14, 14), clicked=self.toggleFullscreen, cursor=Qt.PointingHandCursor, enabled=False)
        self.menuButton = QPushButton(self, toolTip='Menu', cursor=Qt.PointingHandCursor, flat=True, objectName='menuButton', clicked=self.showAppMenu, statusTip='View menu options')
        self.menuButton.setFixedSize(QSize(33, 32))

        audioLayout = QHBoxLayout()
        audioLayout.setContentsMargins(0, 0, 0, 0)
        audioLayout.addWidget(self.muteButton)
        audioLayout.addSpacing(5)
        audioLayout.addWidget(self.volSlider)
        audioLayout.addSpacing(5)
        audioLayout.addWidget(self.fullscreenButton)

        self.toolbar_open = VCToolBarButton('Open', 'Open and load a media file to begin', parent=self)
        self.toolbar_open.clicked.connect(self.openFolder)
        self.toolbar_play = VCToolBarButton('Play', 'Play currently loaded media file', parent=self)
        self.toolbar_play.setEnabled(False)
        self.toolbar_play.clicked.connect(self.playMedia)

        self.toolbar_start = VCToolBarButton('Start Clip', 'Start a new clip from the current timeline position', parent=self)
        self.toolbar_start.setEnabled(False)
        self.toolbar_start.clicked.connect(self.clipStart)

        self.toolbar_end = VCToolBarButton('End Clip', 'End a new clip at the current timeline position', parent=self)
        self.toolbar_end.setEnabled(False)
        self.toolbar_end.clicked.connect(self.clipEnd)

        self.toolbar_save = VCToolBarButton('Save', 'Save clips to a new media file', parent=self)
        self.toolbar_save.setEnabled(False)
        self.toolbar_save.clicked.connect(self.saveProject)


        toolbarLayout = QHBoxLayout()
        toolbarLayout.setContentsMargins(0, 0, 0, 0)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbar_open)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbar_play)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbar_start)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbar_end)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbar_save)
        # toolbarLayout.addStretch(1)
        # toolbarLayout.addWidget(self.toolbar_send)

        self.toolbarGroup = QGroupBox()
        self.toolbarGroup.setLayout(toolbarLayout)
        self.toolbarGroup.setStyleSheet('QGroupBox { border: 0; }')

        self.setToolBarStyle(self.settings.value('toolbarLabels', 'beside', type=str))

        settingsLayout = QHBoxLayout()
        settingsLayout.setSpacing(0)
        settingsLayout.setContentsMargins(0, 0, 0, 0)
        settingsLayout.addWidget(self.osdButton)
        settingsLayout.addWidget(self.thumbnailsButton)

        settingsLayout.addSpacing(5)
        settingsLayout.addWidget(self.menuButton)

        groupLayout = QVBoxLayout()
        groupLayout.addLayout(audioLayout)
        groupLayout.addSpacing(10)
        groupLayout.addLayout(settingsLayout)

        controlsLayout = QHBoxLayout()
        if sys.platform != 'darwin':
            controlsLayout.setContentsMargins(0, 0, 0, 0)
            controlsLayout.addSpacing(5)
        else:
            controlsLayout.setContentsMargins(10, 10, 10, 0)
        # controlsLayout.addLayout(togglesLayout)
        controlsLayout.addSpacing(20)
        controlsLayout.addStretch(1)
        controlsLayout.addWidget(self.toolbarGroup)
        controlsLayout.addStretch(1)
        controlsLayout.addSpacing(20)
        controlsLayout.addLayout(groupLayout)
        if sys.platform != 'darwin':
            controlsLayout.addSpacing(5)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 0)
        layout.addLayout(self.videoLayout)
        layout.addWidget(self.sliderWidget)
        layout.addSpacing(5)
        layout.addLayout(controlsLayout)

        self.setLayout(layout)
        self.videoSlider.initStyle()


    @pyqtSlot()
    def showAppMenu(self) -> None:
        pos = self.menuButton.mapToGlobal(self.menuButton.rect().topLeft())
        pos.setX(pos.x() - self.appmenu.sizeHint().width() + 30)
        pos.setY(pos.y() - 28)
        self.appmenu.popup(pos, self.quitAction)

    def initTheme(self) -> None:
        qApp.setStyle(VideoStyleDark() if self.theme == 'dark' else VideoStyleLight())
        self.fonts = [
            QFontDatabase.addApplicationFont(':/fonts/FuturaLT.ttf'),
            QFontDatabase.addApplicationFont(':/fonts/NotoSans-Bold.ttf'),
            QFontDatabase.addApplicationFont(':/fonts/NotoSans-Regular.ttf')
        ]
        self.style().loadQSS(self.theme)
        QApplication.setFont(QFont('Noto Sans', 12 if sys.platform == 'darwin' else 10, 300))

    def getMPV(self, parent: QWidget=None, file: str=None, start: float=0, pause: bool=True, mute: bool=False,
               volume: int=None) -> mpvWidget:
        widget = mpvWidget(
            parent=parent,
            file=file,
            #vo='opengl-cb',
            pause=pause,
            start=start,
            mute=mute,
            keep_open='always',
            idle=True,
            osd_font=self._osdfont,
            osd_level=0,
            osd_align_x='left',
            osd_align_y='top',
            cursor_autohide=False,
            input_cursor=False,
            input_default_bindings=False,
            stop_playback_on_init_failure=False,
            input_vo_keyboard=False,
            sub_auto=False,
            sid=False,
            video_sync='display-vdrop',
            audio_file_auto=False,
            quiet=True,
            volume=volume if volume is not None else self.parent.startupvol,
            opengl_pbo=self.enablePBO,
            keepaspect=self.keepRatio,
            hwdec=('auto' if self.hardwareDecoding else 'no'))
        widget.durationChanged.connect(self.on_durationChanged)
        widget.positionChanged.connect(self.on_positionChanged)
        return widget

    def _initNoVideo(self) -> None:
        self.novideoWidget = QWidget(self)
        self.novideoWidget.setObjectName('novideoWidget')
        self.novideoWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        openmediaLabel = VCBlinkText('open media to begin', self)
        openmediaLabel.setAlignment(Qt.AlignHCenter)
        _version = 'v{}'.format(qApp.applicationVersion())
        if self.parent.flatpak:
            _version += ' <font size="-1">- FLATPAK</font>'
        versionLabel = QLabel(_version, self)
        versionLabel.setObjectName('novideoversion')
        versionLabel.setAlignment(Qt.AlignRight)
        versionLayout = QHBoxLayout()
        versionLayout.setSpacing(0)
        versionLayout.setContentsMargins(0, 0, 10, 8)
        versionLayout.addWidget(versionLabel)
        novideoLayout = QVBoxLayout(self.novideoWidget)
        novideoLayout.setSpacing(0)
        novideoLayout.setContentsMargins(0, 0, 0, 0)
        novideoLayout.addStretch(20)
        novideoLayout.addWidget(openmediaLabel)
        novideoLayout.addStretch(1)
        novideoLayout.addLayout(versionLayout)

    def _initIcons(self) -> None:
        self.appIcon = qApp.windowIcon()
        self.muteIcon = QIcon(':/images/{}/muted.png'.format(self.theme))
        self.unmuteIcon = QIcon(':/images/{}/unmuted.png'.format(self.theme))
        self.chapterIcon = QIcon(':/images/chapters.png')
        self.upIcon = QIcon(':/images/up.png')
        self.downIcon = QIcon(':/images/down.png')
        self.removeIcon = QIcon(':/images/remove.png')
        self.removeAllIcon = QIcon(':/images/remove-all.png')
        self.openProjectIcon = QIcon(':/images/open.png')
        self.saveProjectIcon = QIcon(':/images/save.png')
        self.filtersIcon = QIcon(':/images/filters.png')
        self.mediaInfoIcon = QIcon(':/images/info.png')
        self.streamsIcon = QIcon(':/images/streams.png')
        self.changelogIcon = QIcon(':/images/changelog.png')
        self.viewLogsIcon = QIcon(':/images/viewlogs.png')
        self.updateCheckIcon = QIcon(':/images/update.png')
        self.keyRefIcon = QIcon(':/images/keymap.png')
        self.fullscreenIcon = QIcon(':/images/{}/fullscreen.png'.format(self.theme))
        self.settingsIcon = QIcon(':/images/settings.png')
        self.quitIcon = QIcon(':/images/quit.png')

    # noinspection PyArgumentList
    def _initActions(self) -> None:
        self.moveItemUpAction = QAction(self.upIcon, 'Move clip up', self, statusTip='Move clip position up in list', triggered=self.moveItemUp, enabled=False)
        self.moveItemDownAction = QAction(self.downIcon, 'Move clip down', self, triggered=self.moveItemDown, statusTip='Move clip position down in list', enabled=False)
        self.removeItemAction = QAction(self.removeIcon, 'Remove selected clip', self, triggered=self.removeItem, statusTip='Remove selected clip from list', enabled=False)
        self.removeAllAction = QAction(self.removeAllIcon, 'Remove all clips', self, triggered=self.clearList, statusTip='Remove all clips for current video', enabled=False)
        self.editChapterAction = QAction(self.chapterIcon, 'Edit chapter', self, triggered=self.videoListDoubleClick, statusTip='Edit the selected chapter name', enabled=False)

        # self.openProjectAction = QAction(self.openProjectIcon, 'Open project file', self, triggered=self.openProject, statusTip='Open a previously saved project file (*.vcp or *.edl)', enabled=True)
        self.saveProjectAction = QAction(self.saveProjectIcon, 'Save project file', self, triggered=self.saveProject, statusTip='Save current work to a project file (*.vcp or *.edl)',  enabled=False)

        self.viewLogsAction = QAction(self.viewLogsIcon, 'View log file', self, triggered=VideoCutter.viewLogs, statusTip='View the application\'s log file')
        self.updateCheckAction = QAction(self.updateCheckIcon, 'Check for updates...', self, statusTip='Check for application updates', triggered=self.updater.check)
        self.aboutQtAction = QAction('About Qt', self, triggered=qApp.aboutQt, statusTip='About Qt')
        self.aboutAction = QAction('About {}'.format(qApp.applicationName()), self, triggered=self.aboutApp, statusTip='About {}'.format(qApp.applicationName()))
        self.keyRefAction = QAction(self.keyRefIcon, 'Keyboard shortcuts', self, triggered=self.showKeyRef, statusTip='View shortcut key bindings')
        self.settingsAction = QAction(self.settingsIcon, 'Settings', self, triggered=self.showSettings, statusTip='Configure application settings')
        self.fullscreenAction = QAction(self.changelogIcon, 'Toggle fullscreen', self, triggered=self.toggleFullscreen, statusTip='Toggle fullscreen display mode', enabled=False)
        self.toggleConsoleAction = QAction(self.changelogIcon, 'Toggle console', self, triggered=self.toggleConsole, statusTip='Toggle console', enabled=True)
        self.quitAction = QAction(self.quitIcon, 'Quit', self, triggered=self.parent.close, statusTip='Quit the application')

    @property
    def _filtersMenu(self) -> QMenu:
        menu = QMenu('Video filters', self)
        self.blackdetectAction = VCFilterMenuAction(QPixmap(':/images/blackdetect.png'), 'BLACKDETECT', 'Create clips via black frame detection',
                                                    'Useful for skipping commercials or detecting scene transitions', self)
        if sys.platform == 'darwin':
            self.blackdetectAction.triggered.connect(lambda: self.configFilters(VideoFilter.BLACKDETECT), Qt.QueuedConnection)
        else:
            self.blackdetectAction.triggered.connect(lambda: self.configFilters(VideoFilter.BLACKDETECT), Qt.DirectConnection)
        self.blackdetectAction.setEnabled(False)
        menu.setIcon(self.filtersIcon)
        menu.addAction(self.blackdetectAction)
        return menu

    def _initMenus(self) -> None:
        self.appmenu.addAction(self.settingsAction)
        self.appmenu.addSeparator()
        self.appmenu.addMenu(self.help_menu)
        self.help_menu.addAction(self.keyRefAction)
        self.help_menu.addAction(self.viewLogsAction)
        self.help_menu.addAction(self.toggleConsoleAction)
        self.help_menu.addAction(self.aboutAction)
        self.help_menu.addAction(self.aboutQtAction)
        self.help_menu.addAction(self.updateCheckAction)
        self.appmenu.addAction(self.quitAction)

        self.clipindex_removemenu.addActions([self.removeItemAction, self.removeAllAction])
        self.clipindex_removemenu.aboutToShow.connect(self.initRemoveMenu)

        if sys.platform in {'win', 'darwin'}:
            self.appmenu.setStyle(QStyleFactory.create('Fusion'))
            self.clipindex_contextmenu.setStyle(QStyleFactory.create('Fusion'))
            self.clipindex_removemenu.setStyle(QStyleFactory.create('Fusion'))

    def _initClipIndexHeader(self) -> None:
        if self.indexLayout == 'left':
            self.listHeaderButtonL.setVisible(False)
            self.listHeaderButtonR.setVisible(True)
        else:
            self.listHeaderButtonL.setVisible(True)
            self.listHeaderButtonR.setVisible(False)

    @pyqtSlot()
    def setClipIndexLayout(self) -> None:
        self.indexLayout = 'left' if self.indexLayout == 'right' else 'right'
        self.settings.setValue('indexLayout', self.indexLayout)
        left = self.videoLayout.takeAt(0)
        spacer = self.videoLayout.takeAt(0)
        right = self.videoLayout.takeAt(0)
        if isinstance(left, QVBoxLayout):
            if self.indexLayout == 'left':
                self.videoLayout.addItem(left)
                self.videoLayout.addItem(spacer)
                self.videoLayout.addItem(right)
            else:
                self.videoLayout.addItem(right)
                self.videoLayout.addItem(spacer)
                self.videoLayout.addItem(left)
        else:
            if self.indexLayout == 'left':
                self.videoLayout.addItem(right)
                self.videoLayout.addItem(spacer)
                self.videoLayout.addItem(left)
            else:
                self.videoLayout.addItem(left)
                self.videoLayout.addItem(spacer)
                self.videoLayout.addItem(right)
        self._initClipIndexHeader()

    def setToolBarStyle(self, labelstyle: str = 'beside') -> None:
        buttonlist = self.toolbarGroup.findChildren(VCToolBarButton)
        [button.setLabelStyle(labelstyle) for button in buttonlist]

    def setRunningTime(self, runtime: str) -> None:
        self.runtimeLabel.setText('<div align="right">{}</div>'.format(runtime))
        self.runtimeLabel.setToolTip('total runtime: {}'.format(runtime))
        self.runtimeLabel.setStatusTip('total running time: {}'.format(runtime))

    def getFileDialogOptions(self) -> QFileDialog.Options:
        options = QFileDialog.HideNameFilterDetails
        if not self.nativeDialogs:
            options |= QFileDialog.DontUseNativeDialog
        # noinspection PyTypeChecker
        return options

    @pyqtSlot()
    def showSettings(self):
        settingsDialog = SettingsDialog(self.videoService, self)
        settingsDialog.exec_()

    @pyqtSlot()
    def initRemoveMenu(self):
        self.removeItemAction.setEnabled(False)
        self.removeAllAction.setEnabled(False)
        if self.cliplist.count():
            self.removeAllAction.setEnabled(True)
            if len(self.cliplist.selectedItems()):
                self.removeItemAction.setEnabled(True)

    def itemMenu(self, pos: QPoint) -> None:
        globalPos = self.cliplist.mapToGlobal(pos)
        self.moveItemUpAction.setEnabled(False)
        self.moveItemDownAction.setEnabled(False)
        self.initRemoveMenu()
        index = self.cliplist.currentRow()
        if index != -1:
            if len(self.cliplist.selectedItems()):
                self.editChapterAction.setEnabled(self.createChapters)
            if not self.inCut:
                if index > 0:
                    self.moveItemUpAction.setEnabled(True)
                if index < self.cliplist.count() - 1:
                    self.moveItemDownAction.setEnabled(True)
        self.clipindex_contextmenu.exec_(globalPos)

    def videoListDoubleClick(self) -> None:
        index = self.cliplist.currentRow()
        modifierPressed = QApplication.keyboardModifiers()
        if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
            # self.setPosition(self.clipTimes[index][1].msecsSinceStartOfDay())
            self.setPosition(self.videoList.videos[self.videoList.currentVideoIndex].clips[index].timeEnd.msecsSinceStartOfDay())
        else:
            name = self.videoList.videos[self.videoList.currentVideoIndex].clips[index].name
            timeStart = self.videoList.videos[self.videoList.currentVideoIndex].clips[index].timeStart
            timeEnd = self.videoList.videos[self.videoList.currentVideoIndex].clips[index].timeEnd

            dialog = VCChapterInputDialog(self, name, timeStart, timeEnd)
            dialog.accepted.connect(lambda: self.on_editChapter(index, dialog.start.time(), dialog.end.time(), dialog.input.text()))
            dialog.exec_()

    def on_editChapter(self, index: int, timeStart: QTime, timeEnd: QTime, clipName: str) -> None:
        if timeEnd < timeStart:
            timeEnd = timeStart.addSecs(1)
        self.videoList.setCurrentVideoClipIndex(index)
        self.videoList.setCurrentVideoClipStartTime(timeStart)
        self.videoList.setCurrentVideoClipEndTime(timeEnd)
        self.videoList.setCurrentVideoClipName(clipName)
        self.videoList.setCurrentVideoClipThumbnail(self.captureImage(self.currentMedia, timeStart))
        self.renderClipIndex()

    def moveItemUp(self) -> None:
        index = self.cliplist.currentRow()
        if index != -1:
            tempVideoItem = self.videoList.videos[self.videoList.currentVideoIndex].clips[index]
            del self.videoList.videos[self.videoList.currentVideoIndex].clips[index]
            self.videoList.videos[self.videoList.currentVideoIndex].clips.insert(index - 1, tempVideoItem)
            self.showText('clip moved up')
            self.renderClipIndex()

    def moveItemDown(self) -> None:
        index = self.cliplist.currentRow()
        if index != -1:

            tempVideoItem = self.videoList.videos[self.videoList.currentVideoIndex].clips[index]
            del self.videoList.videos[self.videoList.currentVideoIndex].clips[index]
            self.videoList.videos[self.videoList.currentVideoIndex].clips.insert(index + 1, tempVideoItem)
            self.showText('clip moved down')
            self.renderClipIndex()

    # def removeVideoClipItem(self) -> None:
    def removeItem(self) -> None:
        index = self.cliplist.currentRow()
        if self.mediaAvailable:
            if self.inCut and index == self.cliplist.count() - 1:
                self.inCut = False
                self.initMediaControls()
        elif len(self.videoList.videos[self.videoList.currentVideoIndex].clips) == 0:
            self.initMediaControls(False)

        del self.videoList.videos[self.videoList.currentVideoIndex].clips[index]

        if len(self.videoList.videos[self.videoList.currentVideoIndex].clips) <= 1:
            self.clipindex_move_up.setDisabled(True)
            self.clipindex_move_down.setDisabled(True)
        if not len(self.videoList.videos[self.videoList.currentVideoIndex].clips):
            self.clipindex_clips_remove.setDisabled(True)

        self.cliplist.takeItem(index)
        self.showText('clip removed')
        self.renderClipIndex()

    def clearList(self) -> None:
        dialog = VCConfirmDialog(self, 'Delete clips', 'Delete all clips of the current video?')
        dialog.accepted.connect(lambda: self.on_clearList())
        dialog.exec_()

    def on_clearList(self) -> None:
        # self.clipTimes.clear()
        self.cliplist.clear()
        self.videoList.videos[self.videoList.currentVideoIndex].clips.clear()

        self.showText('all clips cleared')
        if self.mediaAvailable:
            self.inCut = False
            self.initMediaControls(True)
        else:
            self.initMediaControls(False)

        self.clipindex_clips_remove.setDisabled(True)
        self.clipindex_move_up.setDisabled(True)
        self.clipindex_move_down.setDisabled(True)
        self.renderVideoClipIndex()
        # self.renderClipIndex()

    def projectFilters(self, savedialog: bool = False) -> str:
        if savedialog:
            return 'VidCutter Project (*.vcp);;MPlayer EDL (*.edl)'
        elif self.mediaAvailable:
            return 'Project files (*.edl *.vcp);;VidCutter Project (*.vcp);;MPlayer EDL (*.edl);;All files (*)'
        else:
            return 'VidCutter Project (*.vcp);;All files (*)'

    @staticmethod
    def mediaFilters(initial: bool = False) -> str:
        filters = 'All media files (*.{})'.format(' *.'.join(VideoService.config.filters.get('all')))
        if initial:
            return filters
        filters += ';;{};;All files (*)'.format(';;'.join(VideoService.config.filters.get('types')))
        return filters

    def openFolder(self) -> Optional[Callable]:
        self.folderOpened = False
        cancel, callback = self.saveWarning()
        if cancel:
            if callback is not None:
                return callback()
            else:
                return
        self._dataFolder = QFileDialog.getExistingDirectory(parent=self.parent, caption='Select Folder', directory=QDir.currentPath())
        filepath = os.path.join(self._dataFolder, self._dataFilename)
        with open(filepath, 'rb') as f:
            self.videoList = pickle.load(f)

        self.videoListWidget.renderList(self.videoList)
        self.videoSlider.setUpdatesEnabled(True)
        self.cliplist.clear()

        self.videoSlider.clearRegions()
        self.videoSlider.setEnabled(False)
        self.videoSlider.setSliderPosition(0)

        self.sliderWidget.hideThumbs()
        self.sliderWidget.setEnabled(False)

        self.videoLayout.replaceWidget(self.videoplayerWidget, self.novideoWidget)
        self.frameCounter.hide()
        self.timeCounter.hide()
        self.videoplayerWidget.hide()
        self.novideoWidget.show()
        self.mpvWidget.setEnabled(False)

    def loadMedia(self, item) -> None:
        item_index = self.videoListWidget.row(item)
        self.videoList.setCurrentVideoIndex(item_index)

        if not self.folderOpened:
            self.videoLayout.replaceWidget(self.novideoWidget, self.videoplayerWidget)
            self.frameCounter.show()
            self.timeCounter.show()
            self.videoplayerWidget.show()
            self.novideoWidget.hide()
            self.folderOpened = True

        filepath = self.videoList.currentVideoFilepath(self._dataFolder)
        if not os.path.isfile(filepath):
            return
        self.currentMedia = filepath
        self.currentMediaPreview = filepath + self.previewPostfix
        self.projectDirty, self.projectSaved = False, False
        self.initMediaControls(True)
        self.totalRuntime = 0
        self.taskbar.init()
        self.parent.setWindowTitle('{0} - {1}'.format(qApp.applicationName(), os.path.basename(self.currentMedia)))

        try:
            self.mpvWidget.setEnabled(True)
            self.videoService.setMedia(self.currentMedia)
            self.mpvWidget.play(self.currentMedia)
            self.videoSlider.setEnabled(True)
            self.videoSlider.setFocus()
            self.sliderWidget.setEnabled(True)
            self.mediaAvailable = True
        except InvalidMediaException:
            qApp.restoreOverrideCursor()
            self.initMediaControls(False)
            self.logger.error('Could not load media file', exc_info=True)
            QMessageBox.critical(self.parent, 'Could not load media file',
                                 '<h3>Invalid media file selected</h3><p>All attempts to make sense of the file have '
                                 'failed. Try viewing it in another media player and if it plays as expected please '
                                 'report it as a bug. Use the link in the About VidCutter menu option for details '
                                 'and make sure to include your operating system, video card, the invalid media file '
                                 'and the version of VidCutter you are currently using.</p>')

    def saveProject(self, reboot: bool = False) -> None:
        if self.currentMedia is None:
            return
        self.showText('saving...')
        self.parent.setEnabled(False)
        data_filepath_temporary = os.path.join(self._dataFolder, self._dataFilenameTemp)
        data_filepath = os.path.join(self._dataFolder, self._dataFilename)
        try:
            with open(data_filepath_temporary, 'wb') as f:
                pickle.dump(self.videoList, f)
            shutil.copy(data_filepath_temporary, data_filepath)
            if not reboot:
                self.showText('project file saved')
            self.projectSaved = True
        except OSError:
            self.showText('project save failed')
        self.parent.setEnabled(True)
        qApp.restoreOverrideCursor()

    def editVideoDescription(self):
        index = self.videoListWidget.currentRow()
        modifierPressed = QApplication.keyboardModifiers()
        if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
            self.videoList.setCurrentVideoIndex(index)
            issueClasses = self.videoList.videoIssuesClasses
            checkedIssues = self.videoList.videos[index].issues
            description = self.videoList.videos[index].description
            dialog = VideoDescriptionDialog(self, issueClasses, checkedIssues, description)
            dialog.accepted.connect(lambda: self.on_editVideoDescription(index, dialog.checkedIssuesList, dialog.textField.toPlainText()))
            dialog.exec_()

    def on_editVideoDescription(self, index, issuesList, description):
        self.videoList.videos[index].issues = issuesList
        self.videoList.videos[index].description = description
        self.projectSaved = False
        self.saveProjectAction.setEnabled(True)
        self.toolbar_save.setEnabled(True)


    def setPlayButton(self, playing: bool=False) -> None:
        self.toolbar_play.setup('{} Media'.format('Pause' if playing else 'Play'),
                                'Pause currently playing media' if playing else 'Play currently loaded media',
                                True)

    def playMedia(self) -> None:
        playstate = self.mpvWidget.property('pause')
        self.setPlayButton(playstate)
        self.taskbar.setState(playstate)
        self.timeCounter.clearFocus()
        self.frameCounter.clearFocus()
        self.mpvWidget.pause()

    def playMediaTimeClip(self, index) -> None:
        # if not len(self.clipTimes) or not self.videoList.videos[self.videoList.currentVideoIndex].clipsLength():
        if not self.videoList.videos[self.videoList.currentVideoIndex].clipsLength():
            return

        playstate = self.mpvWidget.property('pause')
        self.clipIsPlaying = True
        self.clipIsPlayingIndex = index
        # self.setPosition(self.clipTimes[index][0].msecsSinceStartOfDay())
        self.setPosition(self.videoList.videos[self.videoList.currentVideoIndex].clips[index].timeStart.msecsSinceStartOfDay())
        if playstate:
            self.setPlayButton(True)
            self.taskbar.setState(True)
            self.timeCounter.clearFocus()
            self.frameCounter.clearFocus()
            self.mpvWidget.pause()

    def showText(self, text: str, duration: int = 3, override: bool = False) -> None:
        if self.mediaAvailable:
            if not self.osdButton.isChecked() and not override:
                return
            if len(text.strip()):
                self.mpvWidget.showText(text, duration)

    def initMediaControls(self, flag: bool = True) -> None:
        self.toolbar_play.setEnabled(flag)
        self.toolbar_start.setEnabled(flag)
        self.toolbar_end.setEnabled(False)
        self.toolbar_save.setEnabled(flag)
        self.fullscreenButton.setEnabled(flag)
        self.fullscreenAction.setEnabled(flag)
        self.videoSlider.clearRegions()
        if flag:
            self.videoSlider.setRestrictValue(0)
        else:
            self.videoSlider.setValue(0)
            self.videoSlider.setRange(0, 0)
            self.timeCounter.reset()
            self.frameCounter.reset()
        self.saveProjectAction.setEnabled(False)

    @pyqtSlot(int)
    def setPosition(self, position: int) -> None:
        if position >= self.videoSlider.restrictValue:
            self.mpvWidget.seek(position / 1000)

    @pyqtSlot(float, int)
    def on_positionChanged(self, progress: float, frame: int) -> None:
        progress *= 1000
        if self.videoSlider.restrictValue < progress or progress == 0:
            self.videoSlider.setValue(int(progress))
            self.timeCounter.setTime(self.delta2QTime(round(progress)).toString(self.timeformat))
            self.frameCounter.setFrame(frame)
            if self.videoSlider.maximum() > 0:
                self.taskbar.setProgress(float(progress / self.videoSlider.maximum()), True)
            if self.clipIsPlayingIndex >= 0:
                current_clip_end = QTime(0, 0, 0).msecsTo(self.videoList.videos[self.videoList.currentVideoIndex].clips[self.clipIsPlayingIndex].timeEnd)
                if progress > current_clip_end:
                    self.playMedia()
                    self.clipIsPlaying = False
                    self.clipIsPlayingIndex = -1


    @pyqtSlot(float, int)
    def on_durationChanged(self, duration: float, frames: int) -> None:
        duration *= 1000
        self.videoSlider.setRange(0, int(duration))
        self.timeCounter.setDuration(self.delta2QTime(round(duration)).toString(self.timeformat))
        self.frameCounter.setFrameCount(frames)
        self.renderClipIndex()
        self.updateClipIndexButtonsState()

    @pyqtSlot()
    @pyqtSlot(QListWidgetItem)
    def editClipVisibility(self, item: QListWidgetItem = None) -> None:
        try:
            item_index = self.cliplist.row(item)
            item_state = item.checkState()

            # self.clipTimes[item_index][5] = item_state
            self.videoList.videos[self.videoList.currentVideoIndex].clips[item_index].visibility = item_state
            self.renderClipIndex()
        except Exception:
            self.doPass()

    @pyqtSlot()
    @pyqtSlot(QListWidgetItem)
    def videosVisibility(self, item) -> None:
        if self.cliplist.clipsHasRendered:
            item_index = self.cliplist.row(item)
            item_state = item.checkState()

            # self.clipTimes[item_index][5] = item_state
            self.videoList.videos[self.videoList.currentVideoIndex].clips[item_index].visibility = item_state

            self.videoSlider.setRegionVizivility(item_index, item_state)
            self.videoSlider.update()

    @pyqtSlot()
    @pyqtSlot(QListWidgetItem)
    def videoListSingleClick(self) -> None:
        try:
            modifierPressed = QApplication.keyboardModifiers()
            row = self.cliplist.currentRow()
            if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
                # self.setPosition(self.clipTimes[row][0].msecsSinceStartOfDay())
                self.setPosition(self.videoList.videos[self.videoList.currentVideoIndex].clips[row].timeStart.msecsSinceStartOfDay())
            elif (modifierPressed & Qt.AltModifier) == Qt.AltModifier:
                self.playMediaTimeClip(row)
            else:
                # if not len(self.clipTimes[row][3]):
                self.videoSlider.selectRegion(row)
        except:
            self.doPass()

    def muteAudio(self) -> None:
        if self.mpvWidget.property('mute'):
            self.showText('audio enabled')
            self.muteButton.setIcon(self.unmuteIcon)
            self.muteButton.setToolTip('Mute')
        else:
            self.showText('audio disabled')
            self.muteButton.setIcon(self.muteIcon)
            self.muteButton.setToolTip('Unmute')
        self.mpvWidget.mute()

    def setVolume(self, vol: int) -> None:
        self.settings.setValue('volume', vol)
        if self.mediaAvailable:
            self.mpvWidget.volume(vol)

    @pyqtSlot(bool)
    def toggleThumbs(self, checked: bool) -> None:
        self.videoSlider.showThumbs = checked
        self.saveSetting('timelineThumbs', checked)
        if checked:
            self.showText('thumbnails enabled')
            self.videoSlider.initStyle()
            if self.mediaAvailable:
                self.videoSlider.reloadThumbs()
        else:
            self.showText('thumbnails disabled')
            self.videoSlider.removeThumbs()
            self.videoSlider.initStyle()

    @pyqtSlot(bool)
    def toggleConsole(self) -> None:
        self.showConsole = not self.showConsole
        if not hasattr(self, 'debugonstart'):
            self.debugonstart = os.getenv('DEBUG', False)
        if self.showConsole:
            self.mpvWidget.setLogLevel('v')
            os.environ['DEBUG'] = '1'
            self.parent.console.show()
        else:
            if not self.debugonstart:
                os.environ['DEBUG'] = '0'
                self.mpvWidget.setLogLevel('error')
            self.parent.console.hide()
        self.saveSetting('showConsole', self.showConsole)

    @pyqtSlot(bool)
    def toggleSmartCut(self, checked: bool) -> None:
        self.smartcut = checked
        self.saveSetting('smartcut', self.smartcut)
        self.smartcutButton.setChecked(self.smartcut)
        self.showText('SmartCut {}'.format('enabled' if checked else 'disabled'))

    @pyqtSlot(list)
    def addScenes(self, scenes: List[list]) -> None:
        if len(scenes):
            [self.videoList.videos[self.videoList.currentVideoIndex].clipAppend(VideoItemClip(scene[0], scene[1], self.captureImage(self.currentMedia, scene[0]), '', 2)) for scene in scenes if len(scene)]
            self.renderClipIndex()
        self.filterProgressBar.done(VCProgressDialog.Accepted)

    @pyqtSlot(VideoFilter)
    def configFilters(self, name: VideoFilter) -> None:
        if name == VideoFilter.BLACKDETECT:
            desc = '<p>Detect video intervals that are (almost) completely black. Can be useful to detect chapter ' \
                   'transitions, commercials, or invalid recordings. You can set the minimum duration of ' \
                   'a detected black interval above to adjust the sensitivity.</p>' \
                   '<p><b>WARNING:</b> this can take a long time to complete depending on the length and quality ' \
                   'of the source media.</p>'
            d = VCDoubleInputDialog(self, 'BLACKDETECT - Filter settings', 'Minimum duration for black scenes:',
                                    self.filter_settings.blackdetect.default_duration,
                                    self.filter_settings.blackdetect.min_duration, 999.9, 1, 0.1, desc, 'secs')
            d.buttons.accepted.connect(
                lambda: self.startFilters('detecting scenes (press ESC to cancel)',
                                          partial(self.videoService.blackdetect, d.value), d))
            d.setFixedSize(435, d.sizeHint().height())
            d.exec_()

    @pyqtSlot(str, partial, QDialog)
    def startFilters(self, progress_text: str, filter_func: partial, config_dialog: QDialog) -> None:
        config_dialog.close()
        self.parent.lock_gui(True)
        self.filterProgress(progress_text)
        filter_func()

    @pyqtSlot()
    def stopFilters(self) -> None:
        self.videoService.killFilterProc()
        self.parent.lock_gui(False)

    def filterProgress(self, msg: str) -> None:
        self.filterProgressBar = VCProgressDialog(self, modal=False)
        self.filterProgressBar.finished.connect(self.stopFilters)
        self.filterProgressBar.setText(msg)
        self.filterProgressBar.setMinimumWidth(600)
        self.filterProgressBar.show()

    def clipStart(self) -> None:
        starttime = self.delta2QTime(self.videoSlider.value())
        clipsNumber = len(self.videoList.videos[self.videoList.currentVideoIndex].clips)
        defaultClipName = 'Squat.' + str(clipsNumber + 1).zfill(3)
        clip = VideoItemClip(starttime, QTime(), self.captureImage(self.currentMedia, starttime), defaultClipName, 0)
        self.videoList.videos[self.videoList.currentVideoIndex].clips.append(clip)
        self.timeCounter.setMinimum(starttime.toString(self.timeformat))
        self.frameCounter.lockMinimum()
        self.clipindex_clips_remove.setDisabled(True)
        self.toolbar_start.setDisabled(True)
        self.toolbar_end.setEnabled(True)
        self.clipindex_move_up.setDisabled(True)
        self.clipindex_move_down.setDisabled(True)
        self.videoSlider.setRestrictValue(self.videoSlider.value(), True)
        self.inCut = True
        self.showText('clip started at {}'.format(starttime.toString(self.timeformat)))
        self.renderClipIndex()
        self.cliplist.scrollToBottom()

    def clipEnd(self) -> None:
        # item = self.clipTimes[len(self.clipTimes) - 1]
        clipItemLast = self.videoList.videos[self.videoList.currentVideoIndex].clipsLast()
        endTime = self.delta2QTime(self.videoSlider.value())
        clipItemLast.timeEnd = endTime
        clipItemLast.visibility = 2

        self.toolbar_start.setEnabled(True)
        self.toolbar_end.setDisabled(True)

        self.updateClipIndexButtonsState()
        self.timeCounter.setMinimum()
        self.videoSlider.setRestrictValue(0, False)
        self.inCut = False
        self.showText('clip ends at {}'.format(endTime.toString(self.timeformat)))
        self.renderClipIndex()
        self.cliplist.scrollToBottom()

    @pyqtSlot()
    @pyqtSlot(bool)
    def setProjectDirty(self, dirty: bool=True) -> None:
        self.projectDirty = dirty

    # noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
    @pyqtSlot(QModelIndex, int, int, QModelIndex, int)
    def syncClipList(self, parent: QModelIndex, start: int, end: int, destination: QModelIndex, row: int) -> None: #should replace syncClipList
        index = row - 1 if start < row else row
        clip = self.videoList.videos[self.videoList.currentVideoIndex].clips.pop(start)
        self.videoList.videos[self.videoList.currentVideoIndex].clips.insert(index, clip)
        if not len(clip.visibility): #????? was clip[3]
            self.videoSlider.switchRegions(start, index)
        self.showText('clip order updated')
        self.renderClipIndex()
        # self.renderVideoClipIndex()

    def updateClipIndexButtonsState(self):
        if self.videoList.videos[self.videoList.currentVideoIndex].clipsLength() > 0:
            self.clipindex_clips_remove.setEnabled(True)
        else:
            self.clipindex_clips_remove.setEnabled(False)

        if self.videoList.videos[self.videoList.currentVideoIndex].clipsLength() > 1:
            self.clipindex_move_up.setEnabled(True)
            self.clipindex_move_down.setEnabled(True)
        else:
            self.clipindex_move_up.setEnabled(False)
            self.clipindex_move_down.setEnabled(False)


    def renderClipIndex(self) -> None: #should replace renderClipIndex()
        self.videoSlider.clearRegions()
        self.totalRuntime = 0
        self.cliplist.renderClips(self.videoList.videos[self.videoList.currentVideoIndex].clips)
        if len(self.videoList.videos[self.videoList.currentVideoIndex].clips) and not self.inCut:
            self.toolbar_save.setEnabled(True)
            self.saveProjectAction.setEnabled(True)
        if self.inCut or len(self.videoList.videos[self.videoList.currentVideoIndex].clips) == 0 or  self.videoList.videos[self.videoList.currentVideoIndex].clips[0].timeEnd.isNull():
            self.toolbar_save.setEnabled(False)
            self.saveProjectAction.setEnabled(False)
        # self.setRunningTime(self.delta2QTime(self.totalRuntime).toString(self.runtimeformat))

    @staticmethod
    def delta2QTime(msecs: Union[float, int]) -> QTime:
        if isinstance(msecs, float):
            msecs = round(msecs * 1000)
        t = QTime(0, 0)
        return t.addMSecs(msecs)

    @staticmethod
    def qtime2delta(qtime: QTime) -> float:
        return timedelta(hours=qtime.hour(), minutes=qtime.minute(), seconds=qtime.second(), milliseconds=qtime.msec()).total_seconds()

    @staticmethod
    def delta2String(td: timedelta) -> str:
        if td is None or td == timedelta.max:
            return ''
        else:
            return '%f' % (td.days * 86400 + td.seconds + td.microseconds / 1000000.)

    def captureImage(self, source: str, frametime: QTime, external: bool = False) -> QPixmapPickle:
        thumbnail = VideoService.captureFrame(self.settings, source, frametime.toString(self.timeformat), external=external)
        return QPixmapPickle(thumbnail)

    @pyqtSlot(bool, str)
    def smartmonitor(self, success: bool = None, outputfile: str = None) -> None:
        if success is not None:
            if not success:
                self.logger.error('SmartCut failed for {}'.format(outputfile))
            self.smartcut_monitor.results.append(success)
        if len(self.smartcut_monitor.results) == len(self.smartcut_monitor.clips) - self.smartcut_monitor.externals:
            if False not in self.smartcut_monitor.results:
                self.joinMedia(self.smartcut_monitor.clips)

    def complete(self, rename: bool=True, filename: str=None) -> None:
        if rename and filename is not None:
            # noinspection PyCallByClass
            QFile.remove(self.finalFilename)
            # noinspection PyCallByClass
            QFile.rename(filename, self.finalFilename)
        self.videoService.finalize(self.finalFilename)
        self.videoSlider.updateProgress()
        self.toolbar_save.setEnabled(True)
        self.parent.lock_gui(False)
        self.notify = JobCompleteNotification(
            self.finalFilename,
            self.sizeof_fmt(int(QFileInfo(self.finalFilename).size())),
            self.delta2QTime(self.totalRuntime).toString(self.runtimeformat),
            self.getAppIcon(encoded=True),
            self)
        self.notify.closed.connect(self.videoSlider.clearProgress)
        self.notify.show()
        if self.smartcut:
            QTimer.singleShot(1000, self.cleanup)
        self.setProjectDirty(False)

    @pyqtSlot(str)
    def completeOnError(self, errormsg: str) -> None:
        if self.smartcut:
            self.videoService.smartabort()
            QTimer.singleShot(1500, self.cleanup)
        self.parent.lock_gui(False)
        self.videoSlider.clearProgress()
        self.toolbar_save.setEnabled(True)
        self.parent.errorHandler(errormsg)

    def cleanup(self) -> None:
        if hasattr(self.videoService, 'smartcut_jobs'):
            delattr(self.videoService, 'smartcut_jobs')
        if hasattr(self, 'smartcut_monitor'):
            delattr(self, 'smartcut_monitor')
        self.videoService.smartcutError = False

    def saveSetting(self, setting: str, checked: bool) -> None:
        self.settings.setValue(setting, 'on' if checked else 'off')

    @pyqtSlot()
    def mediaInfo(self) -> None:
        if self.mediaAvailable:
            if self.videoService.backends.mediainfo is None:
                self.logger.error('mediainfo could not be found on the system')
                QMessageBox.critical(self.parent, 'Missing mediainfo utility',
                                     'The <b>mediainfo</b> command could not be found on your system which '
                                     'is required for this feature to work.<br/><br/>Linux users can simply '
                                     'install the <b>mediainfo</b> package using the package manager you use to '
                                     'install software (e.g. apt, pacman, dnf, zypper, etc.)')
                return
            mediainfo = MediaInfo(media=self.currentMedia, parent=self)
            mediainfo.show()

    @pyqtSlot()
    def selectStreams(self) -> None:
        if self.mediaAvailable and self.videoService.streams:
            if self.hasExternals():
                nostreamstext = '''
                    <style>
                        h2 {{
                            color: {0};
                            font-family: "Futura LT", sans-serif;
                            font-weight: normal;
                        }}
                    </style>
                    <table border="0" cellpadding="6" cellspacing="0" width="350">
                        <tr>
                            <td><h2>Cannot configure stream selection</h2></td>
                        </tr>
                        <tr>
                            <td>
                                Stream selection cannot be configured when external media files
                                are added to your clip index. Remove all external files from your
                                clip index and try again.
                            </td>
                        </tr>
                    </table>'''.format('#C681D5' if self.theme == 'dark' else '#642C68')
                nostreams = QMessageBox(QMessageBox.Critical,
                                        'Stream selection is unavailable',
                                        nostreamstext,
                                        parent=self.parent)
                nostreams.setStandardButtons(QMessageBox.Ok)
                nostreams.exec_()
                return
            streamSelector = StreamSelector(self.videoService, self)
            streamSelector.show()

    def saveWarning(self) -> tuple:
        if self.mediaAvailable and self.projectDirty and not self.projectSaved:
            savewarn = VCMessageBox('Warning', 'Unsaved changes found in project',
                                    'Would you like to save your project?', parent=self)
            savebutton = savewarn.addButton('Save project', QMessageBox.YesRole)
            savewarn.addButton('Do not save', QMessageBox.NoRole)
            cancelbutton = savewarn.addButton('Cancel', QMessageBox.RejectRole)
            savewarn.exec_()
            res = savewarn.clickedButton()
            if res == savebutton:
                return False, self.saveProject
            elif res == cancelbutton:
                return True, None
        return False, None

    @pyqtSlot()
    def showKeyRef(self) -> None:
        msgtext = '<img src=":/images/{}/shortcuts.png" />'.format(self.theme)
        msgbox = QMessageBox(QMessageBox.NoIcon, 'Keyboard shortcuts', msgtext, QMessageBox.Ok, self,
                             Qt.Window | Qt.Dialog | Qt.WindowCloseButtonHint)
        msgbox.setObjectName('shortcuts')
        msgbox.setContentsMargins(10, 10, 10, 10)
        msgbox.setMinimumWidth(400 if self.parent.scale == 'LOW' else 600)
        msgbox.exec_()

    @pyqtSlot()
    def aboutApp(self) -> None:
        about = About(self.videoService, self.mpvWidget, self)
        about.exec_()

    @staticmethod
    def getAppIcon(encoded: bool=False):
        icon = QIcon.fromTheme(qApp.applicationName().lower(), QIcon(':/images/vidcutter-small.png'))
        if not encoded:
            return icon
        iconimg = icon.pixmap(82, 82).toImage()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QBuffer.WriteOnly)
        iconimg.save(buffer, 'PNG')
        base64enc = str(data.toBase64().data(), 'latin1')
        icon = 'data:vidcutter.png;base64,{}'.format(base64enc)
        return icon

    @staticmethod
    def sizeof_fmt(num: float, suffix: chr='B') -> str:
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return "%3.1f %s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f %s%s" % (num, 'Y', suffix)

    @pyqtSlot()
    def viewChangelog(self) -> None:
        changelog = Changelog(self)
        changelog.exec_()

    @staticmethod
    @pyqtSlot()
    def viewLogs() -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(logging.getLoggerClass().root.handlers[0].baseFilename))

    @pyqtSlot()
    def toggleFullscreen(self) -> None:
        if self.mediaAvailable:
            pause = self.mpvWidget.property('pause')
            mute = self.mpvWidget.property('mute')
            vol = self.mpvWidget.property('volume')
            pos = self.videoSlider.value() / 1000
            if self.mpvWidget.originalParent is not None:
                self.mpvWidget.shutdown()
                sip.delete(self.mpvWidget)
                del self.mpvWidget
                self.mpvWidget = self.getMPV(parent=self, file=self.currentMedia, start=pos, pause=pause, mute=mute,
                                             volume=vol)
                self.videoplayerLayout.insertWidget(0, self.mpvWidget)
                self.mpvWidget.originalParent = None
                self.parent.show()
            elif self.mpvWidget.parentWidget() != 0:
                self.parent.hide()
                self.mpvWidget.shutdown()
                self.videoplayerLayout.removeWidget(self.mpvWidget)
                sip.delete(self.mpvWidget)
                del self.mpvWidget
                self.mpvWidget = self.getMPV(file=self.currentMedia, start=pos, pause=pause, mute=mute, volume=vol)
                self.mpvWidget.originalParent = self
                self.mpvWidget.setGeometry(qApp.desktop().screenGeometry(self))
                self.mpvWidget.showFullScreen()

    def toggleOSD(self, checked: bool) -> None:
        self.showText('on-screen display {}'.format('enabled' if checked else 'disabled'), override=True)
        self.saveSetting('enableOSD', checked)

    @property
    def _osdfont(self) -> str:
        fontdb = QFontDatabase()
        return 'DejaVu Sans' if 'DejaVu Sans' in fontdb.families(QFontDatabase.Latin) else 'Noto Sans'

    def doPass(self) -> None:
        pass

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key_Q, Qt.Key_W} and event.modifiers() == Qt.ControlModifier:
            self.parent.close()
            return

        if self.mediaAvailable:

            if event.key() == Qt.Key_Space:
                self.playMedia()
                return

            if event.key() == Qt.Key_Escape and self.isFullScreen():
                self.toggleFullscreen()
                return

            if event.key() == Qt.Key_F:
                self.toggleFullscreen()
                return

            if event.key() == Qt.Key_Home:
                self.setPosition(self.videoSlider.minimum())
                return

            if event.key() == Qt.Key_End:
                self.setPosition(self.videoSlider.maximum())
                return

            if event.key() == Qt.Key_Left:
                self.mpvWidget.frameBackStep()
                self.setPlayButton(False)
                return

            if event.key() == Qt.Key_Down:
                if qApp.queryKeyboardModifiers() == Qt.ShiftModifier:
                    self.mpvWidget.seek(-self.level2Seek, 'relative+exact')
                else:
                    self.mpvWidget.seek(-self.level1Seek, 'relative+exact')
                return

            if event.key() == Qt.Key_Right:
                self.mpvWidget.frameStep()
                self.setPlayButton(False)
                return

            if event.key() == Qt.Key_Up:
                if qApp.queryKeyboardModifiers() == Qt.ShiftModifier:
                    self.mpvWidget.seek(self.level2Seek, 'relative+exact')
                else:
                    self.mpvWidget.seek(self.level1Seek, 'relative+exact')
                return

            if event.key() in {Qt.Key_Return, Qt.Key_Enter} and \
                    (not self.timeCounter.hasFocus() and not self.frameCounter.hasFocus()):
                if self.toolbar_start.isEnabled():
                    self.clipStart()
                elif self.toolbar_end.isEnabled():
                    self.clipEnd()
                return

        super(VideoCutter, self).keyPressEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        if hasattr(self, 'filterProgressBar') and self.filterProgressBar.isVisible():
            self.filterProgressBar.update()
        super(VideoCutter, self).showEvent(event)
