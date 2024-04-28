#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy

from PyQt5.QtCore import pyqtSlot, Qt, QEvent, QModelIndex, QRect, QSize, QTime
from PyQt5.QtGui import QColor, QFont, QMouseEvent, QPainter, QPixmap, QPainterPath
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QSizePolicy, QStyle, QWidget, QComboBox, QListWidgetItem, QHBoxLayout, QVBoxLayout, QTimeEdit, QAbstractSpinBox,
                             QStyledItemDelegate, QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication, QLabel, QLayout)

# from PySide2 import QtGui, QtCore, QtWidgets

from vidcutter.libs.graphicseffects import OpacityEffect
from vidcutter.data_structures.video_item_clip import VideoItemClip


class ClipsListWidgetItem(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.item = QListWidgetItem()
        self.widget = QWidget()

        self.comboBox = QComboBox(self)
        self.comboBox.wheelEvent = lambda event: None
        self.comboBox.setFixedWidth(180)
        self.comboBox.setToolTip('Set clip class name')

        self.checkBox = QCheckBox(self)
        self.checkBox.setToolTip('Timeline clip visibility')

        self.clipClassLayout = QHBoxLayout()
        self.clipClassLayout.addWidget(self.comboBox)
        self.clipClassLayout.setSpacing(10)
        self.clipClassLayout.addWidget(self.checkBox)

        # self.startTimeLabel = QLabel("Start time")
        self.timeStart = QTimeEdit(self)
        self.timeStart.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.timeStart.setDisplayFormat('hh:mm:ss.zzz')
        self.timeStart.setFixedWidth(95)
        self.timeStart.setToolTip('Start time of a clip')
        self.timeStart.wheelEvent = lambda event: None

        # self.endTimeLabel = QLabel("End time")
        self.timeEnd = QTimeEdit(self)
        self.timeEnd.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.timeEnd.setDisplayFormat('hh:mm:ss.zzz')
        self.timeEnd.setFixedWidth(95)
        self.timeEnd.setToolTip('End time of a clip')
        self.timeEnd.wheelEvent = lambda event: None

        self.clipNumber = QLabel()

        self.layoutTime = QVBoxLayout()
        self.layoutTime.addWidget(self.timeStart, 0, Qt.AlignLeft)
        self.layoutTime.addWidget(self.timeEnd, 0, Qt.AlignLeft)
        self.layoutTime.addWidget(self.clipNumber, 0, Qt.AlignLeft)

        self.image_label = QLabel()
        self.image_label.setScaledContents(True)
        # self.image_label.setStyleSheet("""border-radius: 10px; background-color: transparent;""")

        self.layout2 = QHBoxLayout()
        self.layout2.addWidget(self.image_label)
        self.layout2.addLayout(self.layoutTime)

        self.layoutGlobal = QVBoxLayout()
        self.layoutGlobal.addLayout(self.clipClassLayout)
        self.layoutGlobal.addLayout(self.layout2)

        self.layoutGlobal.setSizeConstraint(QLayout.SetFixedSize)
        self.widget.setLayout(self.layoutGlobal)

    def roundedPixmap(self, pixmap, radius=20):
        target = QPixmap(pixmap.size())
        target.fill(Qt.transparent)
        painter = QPainter(target)

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.HighQualityAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        path = QPainterPath()
        path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)

        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)

        return target

    def setComboBoxItems(self, items: list[str]) -> None:
        self.comboBox.addItems(items)

    def setVisibility(self, checked: bool):
        self.checkBox.setChecked(checked)

    def setThumbnail(self, pixmap: QPixmap):
        pixmap = pixmap.scaled(QSize(100, 100), Qt.KeepAspectRatio)
        self.image_label.setPixmap(self.roundedPixmap(pixmap, 10))

    def setTimeStart(self, timeStart: QTime):
        self.timeStart.setTime(timeStart)

    def setTimeEnd(self, timeEnd: QTime):
        self.timeEnd.setTime(timeEnd)

    def setNumber(self, number: int):
        self.clipNumber.setText('clip # ' + str(number))
        currentFont = QFont("Arial", 11, QFont.Bold)
        self.clipNumber.setFont(currentFont)


class VideoClipsListWidget(QListWidget):
    def __init__(self, parent=None):
        super(VideoClipsListWidget, self).__init__(parent)
        # self.itemClicked.connect(self.on_item_clicked)
        self.parent = parent
        self.theme = self.parent.theme
        self._progressBars = []
        self.setMouseTracking(True)
        self.setDropIndicatorShown(True)
        self.setFocus()
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setFixedWidth(235)
        self.setItemDelegate(VideoClipItemStyle(self))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setUniformItemSizes(True)
        self.setDragEnabled(False)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAlternatingRowColors(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setObjectName('cliplist')
        self.setStyleSheet('QListView::item { border: none; }')
        self.opacityEffect = OpacityEffect(0.3)
        self.opacityEffect.setEnabled(False)
        self.setGraphicsEffect(self.opacityEffect)
        self.clipsHasRendered = False
        self.viewport().setAttribute(Qt.WA_Hover)

    def mousePressEvent(self, event):
        self._mouseButton = event.button()
        super(VideoClipsListWidget, self).mousePressEvent(event)

    def renderTimelineVideoCLips(self, videoClipItems: list[VideoItemClip]) -> None:
        self.clipsHasRendered = False
        self.parent.scalableTimeline.clearRegions()

        for itemIndex, videoClip in enumerate(videoClipItems):
            self.parent.scalableTimeline.addClip(videoClip.timeStart.msecsSinceStartOfDay() * 1e-3, videoClip.timeEnd.msecsSinceStartOfDay() * 1e-3, videoClip.visibility)
        self.clipsHasRendered = True

    def renderClips(self, videoClipItems: list[VideoItemClip]) -> None:
        actionClasses = copy.deepcopy(self.parent.videoList.actionClassesLabels)
        actionClasses.append(self.parent.videoList.actionClassUnknownLabel)
        videoIndex = self.parent.videoList.currentVideoIndex
        scrollBarValue = self.verticalScrollBar().value()
        self.clipsHasRendered = False
        self.clear()
        self.parent.scalableTimeline.clearRegions()

        for itemIndex, videoClip in enumerate(videoClipItems):
            briefInfo = 'Here should ba a tooltip'
            listItem = ClipsListWidgetItem()
            if QPixmap.isNull(videoClip.thumbnail):
                listItem.setThumbnail(QPixmap(100, 100))
            else:
                listItem.setThumbnail(videoClip.thumbnail)
            listItem.setToolTip(briefInfo)
            listItem.setComboBoxItems(actionClasses)
            listItem.setVisibility(bool(videoClip.visibility))
            listItem.setTimeStart(videoClip.timeStart)
            listItem.setTimeEnd(videoClip.timeEnd)
            listItem.setNumber(itemIndex + 1)

            currentClassIndex = self.parent.videoList[videoIndex].clips[itemIndex].actionClassIndex
            currentClassIndex = (len(actionClasses) + currentClassIndex) % len(actionClasses)
            listItem.comboBox.setCurrentIndex(currentClassIndex)
            listItem.comboBox.currentIndexChanged.connect(lambda value, index=itemIndex: self.comboBoxIndexChanged(value, index))
            listItem.checkBox.stateChanged.connect(lambda state, index=itemIndex: self.checkBoxStateChanged(state, index))
            listItem.timeStart.timeChanged.connect(lambda time, index=itemIndex: self.timeStartChanged(time, index))
            listItem.timeEnd.timeChanged.connect(lambda time, index=itemIndex: self.timeEndChanged(time, index))
            self.addItem(listItem.item)
            self.setItemWidget(listItem.item, listItem.widget)
            self.parent.scalableTimeline.addClip(videoClip.timeStart.msecsSinceStartOfDay() * 1e-3, videoClip.timeEnd.msecsSinceStartOfDay() * 1e-3, videoClip.visibility)
        self.verticalScrollBar().setValue(scrollBarValue)
        self.clipsHasRendered = True

    def comboBoxIndexChanged(self, value, clipIndex):
        videoIndex = self.parent.videoList.currentVideoIndex
        if len(self.parent.videoList.actionClassesLabels) == value:
            self.parent.videoList[videoIndex].clips[clipIndex].actionClassIndex = -1
        else:
            self.parent.videoList[videoIndex].clips[clipIndex].actionClassIndex = value
        self.parent.scalableTimeline.renderVideoClips(self.parent.videoList[videoIndex].clips)

    def checkBoxStateChanged(self, state, clipIndex: int):
        indexVideo = self.parent.videoList.currentVideoIndex
        self.parent.videoList[indexVideo].clips[clipIndex].visibility = state
        self.parent.scalableTimeline.setClipVisibility(clipIndex, state)

    def timeStartChanged(self, time, clipIndex):
        videoIndex = self.parent.videoList.currentVideoIndex
        clip = self.parent.videoList.videos[videoIndex].clips[clipIndex]
        self.parent.videoList.videos[videoIndex].clips.pop(clipIndex)

        clip.timeStart = time
        newClipIndex = self.parent.videoList.videos[videoIndex].clips.bisect_right(clip)
        self.parent.videoList.videos[videoIndex].clips.add(clip)

        thumbnail = self.parent.captureImage(self.parent.currentMedia, time)
        self.parent.videoList.videos[videoIndex].clips[newClipIndex].thumbnail = thumbnail

        if clipIndex != newClipIndex:
            self.renderClips(self.parent.videoList.videos[videoIndex].clips)
            self.item(newClipIndex).setSelected(True)
            clipsNumber = len(self.parent.videoList.videos[videoIndex].clips)
            scrollBarValueNormalized = float(newClipIndex) / float(clipsNumber)
            scrollBarValue = int(scrollBarValueNormalized * (self.verticalScrollBar().maximum() - self.verticalScrollBar().minimum()))
            self.verticalScrollBar().setValue(scrollBarValue)
            # self.setFocus()
        self.parent.renderVideoClips()

    def timeEndChanged(self, time, clipIndex):
        videoIndex = self.parent.videoList.currentVideoIndex
        self.parent.videoList[videoIndex].clips[clipIndex].timeEnd = time
        self.parent.scalableTimeline.renderVideoClips(self.parent.videoList[videoIndex].clips)

    @pyqtSlot()
    @pyqtSlot(int)
    def updateProgress(self, item: int = None) -> None:
        if self.count():
            if item is None:
                [progress.setValue(progress.value() + 1) for progress in self._progressBars]
            else:
                self._progressBars[item].setValue(self._progressBars[item].value() + 1)

    # @pyqtSlot()
    # def clearProgress(self) -> None:
    #     for progress in self._progressBars:
    #         progress.hide()
    #         progress.deleteLater()
    #     self._progressBars.clear()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.count() > 0:
            if self.indexAt(event.pos()).isValid():
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        super(VideoClipsListWidget, self).mouseMoveEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.EnabledChange:
            self.opacityEffect.setEnabled(not self.isEnabled())

    def clearSelection(self) -> None:
        # self.parent.seekSlider.selectRegion(-1)
        self.parent.removeItemAction.setEnabled(False)
        super(VideoClipsListWidget, self).clearSelection()


class VideoClipItemStyle(QStyledItemDelegate):
    def __init__(self, parent: VideoClipsListWidget = None):
        super(VideoClipItemStyle, self).__init__(parent)
        self.parent = parent
        self.theme = self.parent.theme

    def editorEvent(self, event, model, option, index) -> bool:
        if event.type() == QEvent.MouseButtonRelease:
            pME = QMouseEvent(event)
            if pME.button() == Qt.LeftButton:
                ro = self.getCheckboxRect(option)
                pte = pME.pos()
                if ro.contains(pte):
                    value = bool(index.data(Qt.CheckStateRole))
                    model.setData(index, not value, Qt.CheckStateRole)
                    return True
        return super(VideoClipItemStyle, self).editorEvent(event, model, option, index)

    def getCheckboxRect(self, option: QStyleOptionViewItem) -> QRect:
        optionButton = QStyleOptionButton()
        optionButton.QStyleOption = option
        checkerRectangle = QApplication.style().subElementRect(QStyle.SE_ViewItemCheckIndicator, optionButton)
        return option.rect.adjusted(165, -85, checkerRectangle.width(), checkerRectangle.height())

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        rectangle = option.rect
        penColor = QColor('#323232') if self.theme == 'dark' else Qt.lightGray
        if self.parent.isEnabled():
            if option.state & QStyle.State_Selected:
                painter.setBrush(QColor(150, 78, 190, 200))
            elif option.state & QStyle.State_MouseOver:
                painter.setBrush(QColor(227, 212, 232, 150))
                penColor = Qt.black
            else:
                brushColor = QColor(79, 85, 87, 150) if self.theme == 'dark' else QColor('#EFF0F1')
                painter.setBrush(Qt.transparent if index.row() % 2 == 0 else brushColor)
        painter.setPen(penColor)
        painter.drawRect(rectangle)

    def clipText(self, text: str, painter: QPainter, chapter: bool = False) -> str:
        metrics = painter.fontMetrics()
        return metrics.elidedText(text, Qt.ElideRight, (self.parent.width() - 10 if chapter else 100 - 10))

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(220, 150)


# class ListProgress(QProgressBar):
#     def __init__(self, steps: int, geometry: QRect, parent=None):
#         super(ListProgress, self).__init__(parent)
#         self.setStyle(QStyleFactory.create('Fusion'))
#         self.setRange(0, steps)
#         self.setValue(0)
#         self.setGeometry(geometry)
#         palette = self.palette()
#         palette.setColor(QPalette.Highlight, QColor(100, 44, 104))
#         self.setPalette(palette)
#         self.show()
