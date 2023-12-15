#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import copy
import logging
import os
import sys
import pickle
import shutil
from datetime import timedelta
from functools import partial
from typing import Callable, List, Optional, Union
from sortedcontainers import SortedList

import sip
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QBuffer, QByteArray, QDir, QFile, QFileInfo, QModelIndex, QPoint, QSize, Qt, QTime, QTimer, QUrl)
from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QKeyEvent, QPixmap, QShowEvent
from PyQt5.QtWidgets import (QAction, qApp, QApplication, QDialog, QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy, QStyleFactory,
                             QVBoxLayout, QWidget, QScrollArea)

# noinspection PyUnresolvedReferences
from vidcutter import resources
from vidcutter.widgets.dialogs.about import About
from vidcutter.widgets.dialogs.change_log import Changelog
from vidcutter.widgets.dialogs.media_info import MediaInfo
from vidcutter.media_stream import StreamSelector
from vidcutter.widgets.dialogs.settings import SettingsDialog
from vidcutter.widgets.dialogs.updater import Updater
from vidcutter.widgets.video_clips_list_widget import VideoClipsListWidget
from vidcutter.VideoStyle import VideoStyleDark, VideoStyleLight

from vidcutter.libs.config import Config, InvalidMediaException, VideoFilter
from vidcutter.libs.mpvwidget import mpvWidget
from vidcutter.libs.notifications import JobCompleteNotification
from vidcutter.libs.taskbarprogress import TaskbarProgress
from vidcutter.libs.videoservice import VideoService
from vidcutter.libs.widgets import (VCBlinkText, VCDoubleInputDialog, VCFilterMenuAction, VCFrameCounter, VCMessageBox,
                                    VCProgressDialog, VCTimeCounter, VCToolBarButton, VCToolBarComboBox, VCVolumeSlider, VCConfirmDialog)

from vidcutter.VideoItemClip import VideoItemClip

from vidcutter.widgets.timeline_widget import TimelineWidget
from vidcutter.widgets.video_list_widget import VideoListWidget
from vidcutter.widgets.scalable_timeline_widget import ScalableTimeLine
from vidcutter.QPixmapPickle import QPixmapPickle
from vidcutter.widgets.dialogs.video_info_dialog import VideoDescriptionDialog


class VideoLabelingTool(QWidget):
    errorOccurred = pyqtSignal(str)
    timeformat = 'hh:mm:ss.zzz'
    runtimeformat = 'hh:mm:ss'

    def __init__(self, parent: QMainWindow):
        super(VideoLabelingTool, self).__init__(parent)
        self.setObjectName('videolabelingtool')
        self.logger = logging.getLogger(__name__)
        self.parent = parent
        self.theme = self.parent.theme
        self.workFolder = self.parent.WORKING_FOLDER
        self.settings = self.parent.settings
        self.filter_settings = Config.filter_settings()
        self.currentMedia, self.mediaAvailable, self.mpvError = None, False, False
        self.projectDirty, self.projectSaved, self.debugOnStart = False, False, False
        self.notify = None
        self.fonts = []
        self._dataFolder = ''
        self._dataFilename = 'data.pickle'
        self._dataFilenameTemp = 'data.pickle.tmp'
        self.folderOpened = False
        self.factor = 1
        self.factor_minimum = 1
        self.factor_maximum = 18
        self.duration = 0

        self.initTheme()
        self.updater = Updater(self.parent)

        self.timeline = ScalableTimeLine(self)
        # self.timeline = TimelineWidget(self)
        # self.timeline.initAttributes()
        # self.timeline.sliderMoved.connect(self.setPosition)

        # self.videoSliderWidget = VideoSliderWidget(self, self.videoSlider)
        # self.videoSliderWidget.init_attributes()

        self.sliderWidgetScroll = QScrollArea()
        self.sliderWidgetScroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sliderWidgetScroll.setFixedHeight(62)
        self.sliderWidgetScroll.setWidget(self.timeline)
        self.sliderWidgetScroll.setAlignment(Qt.AlignCenter)
        self.sliderWidgetScroll.setContentsMargins(0, 0, 0, 0)
        self.sliderWidgetScroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.taskbar = TaskbarProgress(self.parent)

        self.videoList = None
        self.videoListWidget = VideoListWidget(parent=self)
        self.videoListWidget.itemDoubleClicked.connect(self.loadMedia)
        self.videoListWidget.itemClicked.connect(self.editVideoDescription)

        self.inCut, self.newproject = False, False
        self.finalFilename = ''
        self.totalRuntime, self.frameRate = 0, 0
        self.notifyInterval = 1000

        self.createChapters = self.settings.value('chapters', 'on', type=str) in {'on', 'true'}
        self.enableOSD = False  # self.settings.value('enableOSD', 'on', type=str) in {'on', 'true'}
        self.hardwareDecoding = self.settings.value('hwdec', 'on', type=str) in {'on', 'auto'}
        self.enablePBO = self.settings.value('enablePBO', 'off', type=str) in {'on', 'true'}
        self.keepRatio = self.settings.value('aspectRatio', 'keep', type=str) == 'keep'
        self.keepClips = self.settings.value('keepClips', 'off', type=str) in {'on', 'true'}
        self.nativeDialogs = self.settings.value('nativeDialogs', 'on', type=str) in {'on', 'true'}
        self.indexLayout = self.settings.value('indexLayout', 'right', type=str)
        self.showConsole = self.settings.value('showConsole', 'off', type=str) in {'on', 'true'}
        self.smartcut = self.settings.value('smartcut', 'off', type=str) in {'on', 'true'}
        self.level1Seek = self.settings.value('level1Seek', 2, type=float)
        self.level2Seek = self.settings.value('level2Seek', 5, type=float)
        self.verboseLogs = self.parent.verboseLogs
        self.lastFolder = self.settings.value('lastFolder', QDir.homePath(), type=str)

        self.videoService = VideoService(self.settings, self)
        self.videoService.progress.connect(self.timeline.updateProgress)
        self.videoService.error.connect(self.completeOnError)
        self.videoService.addScenes.connect(self.addScenes)

        self._initIcons()
        self._initActions()

        self.applicationMenu = QMenu(self.parent)
        self.helpMenu = QMenu('Help n Logs', self.applicationMenu)
        self.clipindex_removemenu = QMenu(self)
        self.clipIndexContextmenu = QMenu(self)
        self._initMenus()
        self._initNoVideo()

        self.videoClipsList = VideoClipsListWidget(parent=self)
        self.videoClipsList.clicked.connect(self.videoListSingleClick)
        self.videoClipsList.doubleClicked.connect(self.videoListDoubleClick)
        self.videoClipsList.customContextMenuRequested.connect(self.itemMenu)
        self.videoClipsList.itemChanged.connect(self.videosVisibility)
        self.videoClipsList.model().rowsInserted.connect(self.setProjectDirty)
        self.videoClipsList.model().rowsRemoved.connect(self.setProjectDirty)
        self.videoClipsList.model().rowsMoved.connect(self.setProjectDirty)
        # self.videoClipsList.model().rowsMoved.connect(self.syncClipList)

        self.videoLayout = QHBoxLayout()
        self.videoLayout.setContentsMargins(0, 0, 0, 0)
        self.videoLayout.addWidget(self.videoListWidget)
        self.videoLayout.addWidget(self.novideoWidget)
        self.videoLayout.addWidget(self.videoClipsList)

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

        self.videoPlayerWidget = QFrame(self)
        self.videoPlayerWidget.setObjectName('videoplayer')
        self.videoPlayerWidget.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.videoPlayerWidget.setLineWidth(0)
        self.videoPlayerWidget.setMidLineWidth(0)
        self.videoPlayerWidget.setVisible(False)
        self.videoPlayerWidget.setLayout(self.videoplayerLayout)

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
        # self.fullscreenButton = QPushButton(objectName='fullscreenButton', icon=self.fullscreenIcon, flat=True, toolTip='Toggle fullscreen', statusTip='Switch to fullscreen video',
        #                                     iconSize=QSize(14, 14), clicked=self.toggleFullscreen, cursor=Qt.PointingHandCursor, enabled=False)
        self.menuButton = QPushButton(self, toolTip='Menu', cursor=Qt.PointingHandCursor, flat=True, objectName='menuButton', clicked=self.showAppMenu, statusTip='View menu options')
        self.menuButton.setFixedSize(QSize(33, 32))

        audioLayout = QHBoxLayout()
        audioLayout.setContentsMargins(0, 0, 0, 0)
        audioLayout.addWidget(self.muteButton)
        audioLayout.addSpacing(0)
        audioLayout.addWidget(self.volSlider)
        # audioLayout.addSpacing(5)
        # audioLayout.addWidget(self.fullscreenButton)

        self.toolbarOpen = VCToolBarButton('Open', 'Open and load a media file to begin', parent=self)
        self.toolbarOpen.clicked.connect(self.openFolder)

        self.toolbarPlay = VCToolBarButton('Play', 'Play currently loaded media file', parent=self)
        self.toolbarPlay.setEnabled(False)
        self.toolbarPlay.clicked.connect(self.playMedia)

        self.playbackSpeedDict = {'0.5x': 0.5, '1x': 1.0, '2x': 2.0, '4x': 4.0, '6x': 6.0, '8x': 8.0}
        self.toolbarPlaybackSpeed = VCToolBarComboBox('Speed', 'Set playback speed', parent=self)  # QComboBox()
        self.toolbarPlaybackSpeed.addItems(self.playbackSpeedDict.keys())
        self.toolbarPlaybackSpeed.setCurrentIndex(1)
        self.toolbarPlaybackSpeed.currentIndexChanged(self.changePlaybackSpeed)
        self.toolbarPlaybackSpeed.setEnabled(False)

        self.toolbarStart = VCToolBarButton('Start Clip', 'Start a new clip from the current timeline position', parent=self)
        self.toolbarStart.setEnabled(False)
        self.toolbarStart.clicked.connect(self.clipStart)

        self.toolbarEnd = VCToolBarButton('End Clip', 'End a new clip at the current timeline position', parent=self)
        self.toolbarEnd.setEnabled(False)
        self.toolbarEnd.clicked.connect(self.clipEnd)

        self.toolbarSave = VCToolBarButton('Save', 'Save clips to a new media file', parent=self)
        self.toolbarSave.setEnabled(False)
        self.toolbarSave.clicked.connect(self.saveProject)

        toolbarLayout = QHBoxLayout()
        toolbarLayout.setContentsMargins(0, 0, 0, 0)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbarOpen)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbarPlay)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbarPlaybackSpeed)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbarStart)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbarEnd)
        toolbarLayout.addStretch(1)
        toolbarLayout.addWidget(self.toolbarSave)

        self.timelineMinusButton = VCToolBarButton('Minus', 'Increase timeline scale', parent=self, has_label=False)
        self.timelineMinusButton.button.setFixedSize(30, 32)
        self.timelineMinusButton.button.setEnabled(False)
        self.timelineMinusButton.clicked.connect(self.toolbarMinus)

        self.timelineFactorLabel = QLabel()
        self.timelineFactorLabel.setText('1')
        self.timelineFactorLabel.setEnabled(False)
        self.timelineFactorLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.timelineFactorLabel.setFixedSize(40, 40)
        self.timelineFactorLabel.setAlignment(Qt.AlignCenter)
        self.timelineFactorLabel.setFont(QFont('Verdana', 12))
        self.timelineFactorLabel.setStyleSheet("font-weight: bold; color: {}".format('black' if self.theme == 'dark' else '#C1C2C4'))

        self.timelinePlusButton = VCToolBarButton('Plus', 'Increase timeline scale', parent=self, has_label=False)
        self.timelinePlusButton.button.setFixedSize(30, 32)
        self.timelinePlusButton.button.setEnabled(False)
        self.timelinePlusButton.clicked.connect(self.toolbarPlus)

        scaleTimelineLayout = QHBoxLayout()
        scaleTimelineLayout.setContentsMargins(0, 0, 0, 0)
        scaleTimelineLayout.addStretch(1)
        scaleTimelineLayout.setContentsMargins(0, 0, 0, 0)
        scaleTimelineLayout.addWidget(self.timelineMinusButton)
        scaleTimelineLayout.addWidget(self.timelineFactorLabel)
        scaleTimelineLayout.addWidget(self.timelinePlusButton)

        self.toolbarGroup = QGroupBox()
        self.toolbarGroup.setLayout(toolbarLayout)
        self.toolbarGroup.setStyleSheet('QGroupBox { border: 0; }')

        self.setToolBarStyle(self.settings.value('toolbarLabels', 'beside', type=str))

        settingsLayout = QHBoxLayout()
        settingsLayout.setSpacing(0)
        settingsLayout.setContentsMargins(0, 0, 0, 0)

        settingsLayout.addSpacing(5)
        settingsLayout.addWidget(self.menuButton)

        groupLayout = QHBoxLayout()
        groupLayout.addLayout(audioLayout)
        groupLayout.addSpacing(10)
        groupLayout.addLayout(settingsLayout)

        controlsLayout = QHBoxLayout()
        if sys.platform != 'darwin':
            controlsLayout.setContentsMargins(0, 0, 0, 0)
            controlsLayout.addSpacing(5)
        else:
            controlsLayout.setContentsMargins(10, 10, 10, 0)
        controlsLayout.addLayout(scaleTimelineLayout)
        controlsLayout.addSpacing(20)
        controlsLayout.addStretch(1)
        controlsLayout.addWidget(self.toolbarGroup)
        controlsLayout.addStretch(1)
        controlsLayout.addSpacing(20)
        controlsLayout.addLayout(groupLayout)
        if sys.platform != 'darwin':
            controlsLayout.addSpacing(5)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 0)
        layout.addLayout(self.videoLayout)
        layout.addWidget(self.sliderWidgetScroll)
        layout.addSpacing(5)
        layout.addLayout(controlsLayout)

        self.setLayout(layout)
        self.timeline.initStyle()
        self.setTimelineSize()

    def setTimelineSize(self):
        windowSize = self.parent.size()
        self.sliderWidgetScroll.setFixedWidth(windowSize.width() - 18)
        self.sliderWidgetScroll.setFixedHeight(126)

        self.timeline.setFixedWidth(self.factor * windowSize.width() - 20)
        self.timeline.setFixedHeight(108)

    def clip(self, val, min_, max_):
        return min_ if val < min_ else max_ if val > max_ else val

    def speedUp(self):
        index = self.toolbarPlaybackSpeed.comboBox.currentIndex()
        index += 1
        index = self.clip(index, 0, len(self.playbackSpeedDict) - 1)
        self.toolbarPlaybackSpeed.comboBox.setCurrentIndex(index)

    def speedDown(self):
        index = self.toolbarPlaybackSpeed.comboBox.currentIndex()
        index -= 1
        index = self.clip(index, 0, len(self.playbackSpeedDict) - 1)
        self.toolbarPlaybackSpeed.comboBox.setCurrentIndex(index)

    @pyqtSlot()
    def toolbarPlus(self):
        factor_ = copy.copy(self.factor)
        if self.factor == 1:
            self.factor += 1
        else:
            self.factor += 2
        self.factor = self.clip(self.factor, self.factor_minimum, self.factor_maximum)
        # sliderValueMillis = int(self.videoSlider.value() / factor_)
        self.setTimelineSize()
        # self.videoSlider.setMaximum(int(self.videoSlider.baseMaximum))
        self.timelineFactorLabel.setText(str(self.factor))
        if self.parent.isEnabled() and self.mediaAvailable:
            self.renderSliderVideoClips()
        # self.setPosition(sliderValueMillis + 1)
        # print('videoSlider.maximum()', self.timeline.maximum())
        # print('self.videoSlider.baseMaximum', self.timeline.baseMaximum)

    @pyqtSlot()
    def toolbarMinus(self):
        factor_ = copy.copy(self.factor)
        if self.factor == 2:
            self.factor -= 1
        else:
            self.factor -= 2
        self.factor = self.clip(self.factor, self.factor_minimum, self.factor_maximum)
        # self.videoSlider.setMaximum(int(self.videoSlider.baseMaximum))
        self.timelineFactorLabel.setText(str(self.factor))
        self.setTimelineSize()
        if self.parent.isEnabled() and self.mediaAvailable:
            self.renderSliderVideoClips()
        # self.setPosition(sliderValueMillis - 1)
        # print('videoSlider.maximum()', self.timeline.maximum())
        # print('self.videoSlider.baseMaximum', self.timeline.baseMaximum)

    @pyqtSlot()
    def showAppMenu(self) -> None:
        pos = self.menuButton.mapToGlobal(self.menuButton.rect().topLeft())
        pos.setX(pos.x() - self.applicationMenu.sizeHint().width() + 30)
        pos.setY(pos.y() - 28)
        self.applicationMenu.popup(pos, self.quitAction)

    def initTheme(self) -> None:
        qApp.setStyle(VideoStyleDark() if self.theme == 'dark' else VideoStyleLight())
        self.fonts = [
            QFontDatabase.addApplicationFont(':/fonts/FuturaLT.ttf'),
            QFontDatabase.addApplicationFont(':/fonts/NotoSans-Bold.ttf'),
            QFontDatabase.addApplicationFont(':/fonts/NotoSans-Regular.ttf')
        ]
        self.style().loadQSS(self.theme)
        QApplication.setFont(QFont('Noto Sans', 12 if sys.platform == 'darwin' else 10, 300))

    def getMPV(self, parent: QWidget = None, file: str = None, start: float = 0, pause: bool = True, mute: bool = False,
               volume: int = None) -> mpvWidget:
        widget = mpvWidget(
            parent=parent,
            file=file,
            # vo='opengl-cb',
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
        # self.moveItemUpAction = QAction(self.upIcon, 'Move clip up', self, statusTip='Move clip position up in list', triggered=self.moveItemUp, enabled=False)
        # self.moveItemDownAction = QAction(self.downIcon, 'Move clip down', self, triggered=self.moveItemDown, statusTip='Move clip position down in list', enabled=False)
        # self.editChapterAction = QAction(self.chapterIcon, 'Edit chapter', self, triggered=self.videoListDoubleClick, statusTip='Edit the selected chapter name', enabled=False)
        self.removeItemAction = QAction(self.removeIcon, 'Remove selected clip', self, triggered=self.removeItem, statusTip='Remove selected clip from list', enabled=False)
        self.removeAllAction = QAction(self.removeAllIcon, 'Remove all clips', self, triggered=self.clearList, statusTip='Remove all clips for current video', enabled=False)
        self.toggleVisibilityAction = QAction(self.removeAllIcon, 'Toggle clips visibility', self, triggered=self.toggleClipsVisibility, statusTip='Remove all clips for current video', enabled=False)
        self.turnVisibilityOnAction = QAction(self.removeAllIcon, 'Turn clips visibility ON', self, triggered=self.turnClipsVisibilityOn, statusTip='Remove all clips for current video', enabled=False)
        self.turnVisibilityOffAction = QAction(self.removeAllIcon, 'Turn clips visibility OFF', self, triggered=self.turnClipsVisibilityOff, statusTip='Remove all clips for current video', enabled=False)

        # self.openProjectAction = QAction(self.openProjectIcon, 'Open project file', self, triggered=self.openProject, statusTip='Open a previously saved project file (*.vcp or *.edl)', enabled=True)
        self.saveProjectAction = QAction(self.saveProjectIcon, 'Save project file', self, triggered=self.saveProject, statusTip='Save current work to a project file (*.vcp or *.edl)', enabled=False)

        self.viewLogsAction = QAction(self.viewLogsIcon, 'View log file', self, triggered=VideoLabelingTool.viewLogs, statusTip='View the application\'s log file')
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
        self.applicationMenu.addAction(self.settingsAction)
        self.applicationMenu.addSeparator()
        self.applicationMenu.addMenu(self.helpMenu)
        self.helpMenu.addAction(self.keyRefAction)
        self.helpMenu.addAction(self.viewLogsAction)
        self.helpMenu.addAction(self.toggleConsoleAction)
        self.helpMenu.addAction(self.aboutAction)
        self.helpMenu.addAction(self.aboutQtAction)
        self.helpMenu.addAction(self.updateCheckAction)
        self.applicationMenu.addAction(self.quitAction)

        self.clipIndexContextmenu.addAction(self.removeItemAction)
        self.clipIndexContextmenu.addAction(self.removeAllAction)
        self.clipIndexContextmenu.addSeparator()
        self.clipIndexContextmenu.addAction(self.toggleVisibilityAction)
        self.clipIndexContextmenu.addAction(self.turnVisibilityOnAction)
        self.clipIndexContextmenu.addAction(self.turnVisibilityOffAction)

        self.clipindex_removemenu.addActions([self.removeItemAction, self.removeAllAction])
        self.clipindex_removemenu.aboutToShow.connect(self.initRemoveMenu)

        if sys.platform in {'win', 'darwin'}:
            self.applicationMenu.setStyle(QStyleFactory.create('Fusion'))
            self.clipIndexContextmenu.setStyle(QStyleFactory.create('Fusion'))
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
        self.toggleVisibilityAction.setEnabled(False)
        self.turnVisibilityOnAction.setEnabled(False)
        self.turnVisibilityOffAction.setEnabled(False)

        if self.videoClipsList.count():
            self.removeAllAction.setEnabled(True)
            self.toggleVisibilityAction.setEnabled(True)
            self.turnVisibilityOnAction.setEnabled(True)
            self.turnVisibilityOffAction.setEnabled(True)

            if len(self.videoClipsList.selectedItems()):
                self.removeItemAction.setEnabled(True)

    def itemMenu(self, pos: QPoint) -> None:
        globalPos = self.videoClipsList.mapToGlobal(pos)
        self.initRemoveMenu()
        index = self.videoClipsList.currentRow()
        # if index != -1:
        #     if len(self.videoClipsList.selectedItems()):
        #         self.editChapterAction.setEnabled(self.createChapters)
        #     if not self.inCut:
        #         if index > 0:
        #             self.moveItemUpAction.setEnabled(True)
        #         if index < self.videoClipsList.count() - 1:
        #             self.moveItemDownAction.setEnabled(True)
        self.clipIndexContextmenu.exec_(globalPos)

    def videoListDoubleClick(self) -> None:
        index = self.videoClipsList.currentRow()
        modifierPressed = QApplication.keyboardModifiers()
        if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
            self.setPosition(self.videoList.videos[self.videoList.currentVideoIndex].clips[index].timeEnd.msecsSinceStartOfDay())

    def on_editChapter(self, index: int, timeStart: QTime, timeEnd: QTime, clipName: str) -> None:
        if timeEnd < timeStart:
            timeEnd = timeStart.addSecs(1)
        self.videoList.setCurrentVideoClipIndex(index)
        self.videoList.setCurrentVideoClipStartTime(timeStart)
        self.videoList.setCurrentVideoClipEndTime(timeEnd)
        self.videoList.setCurrentVideoClipName(clipName)
        self.videoList.setCurrentVideoClipThumbnail(self.captureImage(self.currentMedia, timeStart))
        self.renderVideoClips()

    def moveItemUp(self) -> None:
        index = self.videoClipsList.currentRow()
        if index != -1:
            tempVideoItem = self.videoList.videos[self.videoList.currentVideoIndex].clips[index]
            del self.videoList.videos[self.videoList.currentVideoIndex].clips[index]
            self.videoList.videos[self.videoList.currentVideoIndex].clips.insert(index - 1, tempVideoItem)
            self.renderVideoClips()

    def moveItemDown(self) -> None:
        index = self.videoClipsList.currentRow()
        if index != -1:
            tempVideoItem = self.videoList.videos[self.videoList.currentVideoIndex].clips[index]
            del self.videoList.videos[self.videoList.currentVideoIndex].clips[index]
            self.videoList.videos[self.videoList.currentVideoIndex].clips.insert(index + 1, tempVideoItem)
            self.renderVideoClips()

    # def removeVideoClipItem(self) -> None:
    def removeItem(self) -> None:
        index = self.videoClipsList.currentRow()
        if self.mediaAvailable:
            if index == self.videoClipsList.count() - 1:
                self.initMediaControls()
        elif len(self.videoList.videos[self.videoList.currentVideoIndex].clips) == 0:
            self.initMediaControls(False)

        self.videoList.videos[self.videoList.currentVideoIndex].clips.pop(index)
        self.videoClipsList.takeItem(index)
        self.renderVideoClips()

    def clearList(self) -> None:
        dialog = VCConfirmDialog(self, 'Delete clips', 'Delete all clips of the current video?')
        dialog.accepted.connect(lambda: self.on_clearList())
        dialog.exec_()

    def toggleClipsVisibility(self) -> None:
        for index_clip in range(len(self.videoList.videos[self.videoList.currentVideoIndex].clips)):
            new_visibility = 2 - self.videoList.videos[self.videoList.currentVideoIndex].clips[index_clip].visibility
            self.videoList.videos[self.videoList.currentVideoIndex].clips[index_clip].visibility = new_visibility
        self.renderVideoClips()

    def turnClipsVisibilityOn(self) -> None:
        for index_clip in range(len(self.videoList.videos[self.videoList.currentVideoIndex].clips)):
            self.videoList.videos[self.videoList.currentVideoIndex].clips[index_clip].visibility = 2
        self.renderVideoClips()

    def turnClipsVisibilityOff(self) -> None:
        for index_clip in range(len(self.videoList.videos[self.videoList.currentVideoIndex].clips)):
            self.videoList.videos[self.videoList.currentVideoIndex].clips[index_clip].visibility = 0
        self.renderVideoClips()

    def on_clearList(self) -> None:
        # self.clipTimes.clear()
        self.videoClipsList.clear()
        self.videoList.videos[self.videoList.currentVideoIndex].clips.clear()

        if self.mediaAvailable:
            self.inCut = False
            self.initMediaControls(True)
        else:
            self.initMediaControls(False)

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

        self.timeline.setUpdatesEnabled(True)
        self.videoClipsList.clear()

        self.videoListWidget.renderList(self.videoList)
        self.videoLayout.replaceWidget(self.videoPlayerWidget, self.novideoWidget)
        self.frameCounter.hide()
        self.timeCounter.hide()
        self.videoPlayerWidget.hide()
        self.novideoWidget.show()
        self.mpvWidget.setEnabled(False)
        self.mediaAvailable = False
        self.initMediaControls(False)

        if self._dataFolder is not None:
            self.lastFolder = QFileInfo(self._dataFolder).absolutePath()
            print('lastFolder', self.lastFolder)

    def loadMedia(self, item) -> None:
        item_index = self.videoListWidget.row(item)
        self.videoList.setCurrentVideoIndex(item_index)
        if not self.folderOpened:
            self.videoLayout.replaceWidget(self.novideoWidget, self.videoPlayerWidget)
            self.frameCounter.show()
            self.timeCounter.show()
            self.videoPlayerWidget.show()
            self.novideoWidget.hide()
            self.folderOpened = True

        filepath = self.videoList.currentVideoFilepath(self._dataFolder)
        if not os.path.isfile(filepath):
            return
        self.currentMedia = filepath
        self.projectDirty, self.projectSaved = False, False
        self.initMediaControls(True)
        self.totalRuntime = 0
        # self.setRunningTime(self.delta2QTime(self.totalRuntime).toString(self.runtimeformat))
        self.taskbar.init()
        self.parent.setWindowTitle(f'video #{item_index + 1}  ::  {os.path.basename(self.currentMedia)}')
        # self.parent.setWindowTitle('{0} - {1}'.format(str(item_index), os.path.basename(self.currentMedia)))

        try:
            self.videoList.videos[self.videoList.currentVideoIndex].clips = SortedList(self.videoList.videos[self.videoList.currentVideoIndex].clips)
            self.mpvWidget.setEnabled(True)
            self.mpvWidget.play(self.currentMedia)
            self.videoService.setMedia(self.currentMedia)

            self.timeline.setEnabled(True)
            self.timeline.currentRectangleIndex = -1
            self.timeline.setFocus()

            self.mediaAvailable = True
            self.timelineMinusButton.button.setEnabled(True)
            self.timelineFactorLabel.setStyleSheet("font-weight: bold; color: light grey")
            self.timelineFactorLabel.setStyleSheet("font-weight: bold; color: {}".format('light grey' if self.theme == 'dark' else 'black'))
            self.timelinePlusButton.button.setEnabled(True)
            self.toolbarPlaybackSpeed.setEnabled(True)
            self.setPosition(self.timeline.minimum())
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

        # self.mpvWidget.mpv.playbackSpeed(4.0)

    def saveProject(self, reboot: bool = False) -> None:
        if self.projectSaved:
            return
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
            issueClasses = self.videoList.video_issues_classes
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
        self.toolbarSave.setEnabled(True)

    def setPlayButton(self, playing: bool = False) -> None:
        self.toolbarPlay.setup('{} Media'.format('Pause' if playing else 'Play'), 'Pause currently playing media' if playing else 'Play currently loaded media', True)
        pass

    def playMedia(self) -> None:
        playState = self.mpvWidget.property('pause')
        self.setPlayButton(playState)
        self.taskbar.setState(playState)
        self.timeCounter.clearFocus()
        self.frameCounter.clearFocus()
        self.mpvWidget.pause()
        # self.mpvWidget.setProperty('pause', playState)

    def changePlaybackSpeed(self, index) -> None:
        speedValue = list(self.playbackSpeedDict.values())[index]
        self.mpvWidget.option('speed', speedValue)

    def playMediaTimeClip(self, index) -> None:
        if not len(self.videoList.videos[self.videoList.currentVideoIndex]):
            return
        playstate = self.mpvWidget.property('pause')
        self.clipIsPlaying = True
        self.clipIsPlayingIndex = index
        self.setPosition(self.videoList.videos[self.videoList.currentVideoIndex].clips[index].timeStart.msecsSinceStartOfDay())
        if playstate:
            self.setPlayButton(True)
            self.taskbar.setState(True)
            self.timeCounter.clearFocus()
            self.frameCounter.clearFocus()
            self.mpvWidget.pause()

    def showText(self, text: str, duration: int = 3, override: bool = False) -> None:
        if self.mediaAvailable and len(text.strip()):
            self.mpvWidget.showText(text, duration)

    def initMediaControls(self, flag: bool = True) -> None:
        self.toolbarPlay.setEnabled(flag)
        self.toolbarStart.setEnabled(flag)
        self.toolbarEnd.setEnabled(False)
        self.toolbarSave.setEnabled(flag)
        # self.fullscreenButton.setEnabled(flag)
        self.fullscreenAction.setEnabled(flag)
        self.timeline.clearRegions()
        if flag:
            self.timeline.setRestrictValue(0)
        else:
            self.timeline.setValue(0)
            self.timeline.setRange(0, 0)
            self.timeCounter.reset()
            self.frameCounter.reset()
        self.saveProjectAction.setEnabled(False)

    @pyqtSlot(int)
    def setPosition(self, position: int) -> None:
        # print('setPosition', position)
        if position >= self.timeline.restrictValue:
            self.mpvWidget.seek(position / 1e3)
        # self.update()
        # self.repaint()

    @pyqtSlot(float, int)
    def on_positionChanged(self, progress: float, frame: int) -> None:
        progress *= 1000
        if self.timeline.restrictValue < progress or progress == 0:
            print('on_positionChanged.progress:', progress)
            self.timeline.setValue(int(progress))
            self.timeCounter.setTime(self.delta2QTime(round(progress)).toString(self.timeformat))
            self.frameCounter.setFrame(frame)
            if self.clipIsPlayingIndex >= 0:
                currentClipEnd = QTime(0, 0, 0).msecsTo(self.videoList.videos[self.videoList.currentVideoIndex].clips[self.clipIsPlayingIndex].timeEnd)
                if progress > currentClipEnd:
                    self.playMedia()
                    self.clipIsPlaying = False
                    self.clipIsPlayingIndex = -1

    @pyqtSlot(float, int)
    def on_durationChanged(self, duration: float, frames: int) -> None:
        self.duration = duration
        duration *= 1000
        self.timeline.setRange(0, int(duration))
        # self.videoSlider.baseMaximum = int(duration)
        # print('on_durationChanged', duration)
        # print('on_durationChanged, maximum', self.timeline.maximum())
        # self.videoSlider.setMaximum(10 * int(duration))
        self.timeCounter.setDuration(self.delta2QTime(round(duration)).toString(self.timeformat))
        self.frameCounter.setFrameCount(frames)
        self.renderVideoClips()

    @pyqtSlot()
    @pyqtSlot(QListWidgetItem)
    def editClipVisibility(self, item: QListWidgetItem = None) -> None:
        try:
            itemIndex = self.videoClipsList.row(item)
            itemState = item.checkState()
            # self.clipTimes[itemIndex][5] = itemState
            self.videoList.videos[self.videoList.currentVideoIndex].clips[itemIndex].visibility = itemState
            self.renderVideoClips()
        except Exception:
            self.doPass()

    @pyqtSlot()
    @pyqtSlot(QListWidgetItem)
    def videosVisibility(self, item) -> None:
        if self.videoClipsList.clipsHasRendered:
            itemIndex = self.videoClipsList.row(item)
            itemState = item.checkState()

            # self.clipTimes[itemIndex][5] = itemState
            self.videoList.videos[self.videoList.currentVideoIndex].clips[itemIndex].visibility = itemState

            self.timeline.setRegionVizivility(itemIndex, itemState)
            self.timeline.update()

    @pyqtSlot()
    @pyqtSlot(QListWidgetItem)
    def videoListSingleClick(self) -> None:
        try:
            modifierPressed = QApplication.keyboardModifiers()
            row = self.videoClipsList.currentRow()
            if (modifierPressed & Qt.ControlModifier) == Qt.ControlModifier:
                self.setPosition(self.videoList.videos[self.videoList.currentVideoIndex].clips[row].timeStart.msecsSinceStartOfDay())
            elif (modifierPressed & Qt.AltModifier) == Qt.AltModifier:
                self.playMediaTimeClip(row)
            else:
                # if not len(self.clipTimes[row][3]):
                self.timeline.selectRegion(row)
        except:
            self.doPass()

    def muteAudio(self) -> None:
        if self.mpvWidget.property('mute'):
            self.muteButton.setIcon(self.unmuteIcon)
            self.muteButton.setToolTip('Mute')
        else:
            self.muteButton.setIcon(self.muteIcon)
            self.muteButton.setToolTip('Unmute')
        self.mpvWidget.mute()

    def setVolume(self, vol: int) -> None:
        self.settings.setValue('volume', vol)
        if self.mediaAvailable:
            self.mpvWidget.volume(vol)

    @pyqtSlot(bool)
    def toggleConsole(self) -> None:
        self.showConsole = not self.showConsole
        if not hasattr(self, 'debugOnStart'):
            self.debugOnStart = os.getenv('DEBUG', False)
        if self.showConsole:
            self.mpvWidget.setLogLevel('v')
            os.environ['DEBUG'] = '1'
            self.parent.console.show()
        else:
            if not self.debugOnStart:
                os.environ['DEBUG'] = '0'
                self.mpvWidget.setLogLevel('error')
            self.parent.console.hide()
        self.saveSetting('showConsole', self.showConsole)

    # @pyqtSlot(bool)
    # def toggleSmartCut(self, checked: bool) -> None:
    #     self.smartcut = checked
    #     self.saveSetting('smartcut', self.smartcut)
    #     self.smartcutButton.setChecked(self.smartcut)
    # self.showText('SmartCut {}'.format('enabled' if checked else 'disabled'))

    @pyqtSlot(list)
    def addScenes(self, scenes: List[list]) -> None:
        if len(scenes):
            [self.videoList.videos[self.videoList.currentVideoIndex].clipAppend(VideoItemClip(scene[0], scene[1], self.captureImage(self.currentMedia, scene[0]), '', 2)) for scene in scenes if len(scene)]
            self.renderVideoClips()
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
        startTime = self.delta2QTime(self.timeline.value())
        clipsNumber = len(self.videoList.videos[self.videoList.currentVideoIndex].clips)
        defaultClipName = 'Other'

        clip = VideoItemClip(startTime, QTime(), self.captureImage(self.currentMedia, startTime), defaultClipName, 0)
        bisect_index = self.videoList.videos[self.videoList.currentVideoIndex].clips.bisect_right(clip)
        self.videoList.videos[self.videoList.currentVideoIndex].bisect_index = bisect_index
        self.videoList.videos[self.videoList.currentVideoIndex].clips.add(clip)

        self.timeCounter.setMinimum(startTime.toString(self.timeformat))
        self.frameCounter.lockMinimum()

        self.toolbarStart.setDisabled(True)
        self.toolbarEnd.setEnabled(True)

        self.timeline.setRestrictValue(self.timeline.value(), True)
        self.inCut = True

        # sorted(self.videoList.videos[self.videoList.currentVideoIndex].clips)
        self.renderVideoClips()
        # self.videoClipsList.scrollToBottom()

    def clipEnd(self) -> None:
        # item = self.clipTimes[len(self.clipTimes) - 1]
        # clip_item_last = self.videoList.videos[self.videoList.currentVideoIndex].bisect_index  # .clipsLast()
        bisect_index = self.videoList.videos[self.videoList.currentVideoIndex].bisect_index
        time_end = self.delta2QTime(self.timeline.value())
        self.videoList.videos[self.videoList.currentVideoIndex].clips[bisect_index].timeEnd = time_end
        self.videoList.videos[self.videoList.currentVideoIndex].clips[bisect_index].visibility = 2

        self.toolbarStart.setEnabled(True)
        self.toolbarEnd.setDisabled(True)
        self.timeCounter.setMinimum()
        self.timeline.setRestrictValue(0, False)
        self.inCut = False
        self.renderVideoClips()
        self.videoClipsList.scrollToBottom()

    @pyqtSlot()
    @pyqtSlot(bool)
    def setProjectDirty(self, dirty: bool = True) -> None:
        print('setProjectDirty')
        self.projectDirty = dirty

    # noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
    # @pyqtSlot(QModelIndex, int, int, QModelIndex, int)
    # def syncClipList(self, parent: QModelIndex, start: int, end: int, destination: QModelIndex, row: int) -> None: #should replace syncClipList
    #     index = row - 1 if start < row else row
    #     clip = self.videoList.videos[self.videoList.currentVideoIndex].clips.pop(start)
    #     self.videoList.videos[self.videoList.currentVideoIndex].clips.insert(index, clip)
    #     if not len(clip.visibility):
    #         self.timeline.switchRegions(start, index)
    #     self.renderVideoClips()

    def renderSliderVideoClips(self) -> None:
        if not self.mediaAvailable:
            return
        self.timeline.clearRegions()
        self.totalRuntime = 0
        # force to update sorted list
        self.videoClipsList.renderSliderVideoCLips(self.videoList.videos[self.videoList.currentVideoIndex].clips)

    def renderVideoClips(self) -> None:
        if not self.mediaAvailable:
            return
        self.timeline.clearRegions()
        self.totalRuntime = 0
        # force to update sorted list
        self.videoClipsList.renderClips(self.videoList.videos[self.videoList.currentVideoIndex].clips)

        if len(self.videoList.videos[self.videoList.currentVideoIndex].clips) and not self.inCut:
            self.toolbarSave.setEnabled(True)
            self.saveProjectAction.setEnabled(True)
        if self.inCut or len(self.videoList.videos[self.videoList.currentVideoIndex].clips) == 0 or self.videoList.videos[self.videoList.currentVideoIndex].clips[0].timeEnd.isNull():
            self.toolbarSave.setEnabled(False)
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

    def complete(self, rename: bool = True, filename: str = None) -> None:
        if rename and filename is not None:
            # noinspection PyCallByClass
            QFile.remove(self.finalFilename)
            # noinspection PyCallByClass
            QFile.rename(filename, self.finalFilename)
        self.videoService.finalize(self.finalFilename)
        self.timeline.updateProgress()
        self.toolbarSave.setEnabled(True)
        self.parent.lock_gui(False)
        self.notify = JobCompleteNotification(
            self.finalFilename,
            self.sizeof_fmt(int(QFileInfo(self.finalFilename).size())),
            self.delta2QTime(self.totalRuntime).toString(self.runtimeformat),
            self.getAppIcon(encoded=True),
            self)
        self.notify.closed.connect(self.timeline.clearProgress)
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
        self.timeline.clearProgress()
        self.toolbarSave.setEnabled(True)
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
    def getAppIcon(encoded: bool = False):
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
    def sizeof_fmt(num: float, suffix: chr = 'B') -> str:
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
            pos = self.timeline.value() / 1000
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
                self.setPosition(self.timeline.minimum())
                return

            if event.key() == Qt.Key_End:
                print('Qt.Key_End', 'self.videoSlider.width():', self.timeline.width(), 'self.videoSlider.maximum()', self.timeline.maximum())
                self.setPosition(self.timeline.maximum())
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

            # if event.key() in {Qt.Key_Return, Qt.Key_Enter, Qt.Key_C} and \
            if event.key() in {Qt.Key_C} and \
                    (not self.timeCounter.hasFocus() and not self.frameCounter.hasFocus()):
                if self.toolbarStart.isEnabled():
                    self.clipStart()
                elif self.toolbarEnd.isEnabled():
                    self.clipEnd()
                return

            if event.key() == Qt.Key_Plus and qApp.queryKeyboardModifiers() == Qt.ControlModifier:  # and  (not self.timeCounter.hasFocus() and not self.frameCounter.hasFocus()):
                self.toolbarPlus()
                return

            if event.key() == Qt.Key_Minus and qApp.queryKeyboardModifiers() == Qt.ControlModifier:  # and  (not self.timeCounter.hasFocus() and not self.frameCounter.hasFocus()):
                self.toolbarMinus()
                return

            if event.key() == Qt.Key_Plus and qApp.queryKeyboardModifiers() == Qt.AltModifier:
                self.speedUp()
                return

            if event.key() == Qt.Key_Minus and qApp.queryKeyboardModifiers() == Qt.AltModifier:
                self.speedDown()
                return

        super(VideoLabelingTool, self).keyPressEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        if hasattr(self, 'filterProgressBar') and self.filterProgressBar.isVisible():
            self.filterProgressBar.update()
        super(VideoLabelingTool, self).showEvent(event)

    def fixThumbnails(self, clipList):
        """
        Just in case something went wrong with thumbnails, ue this method.
        But this means something wrong with the code, this case should not arise
        """
        pass
