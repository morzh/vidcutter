#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import sys
import copy

from PyQt5.QtCore import pyqtSlot, Qt, QEvent, QModelIndex, QRect, QSize, QTime, QPoint
from PyQt5.QtGui import QColor, QFont, QIcon, QMouseEvent, QPainter, QPalette, QPen, QResizeEvent, QPixmap, QContextMenuEvent
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QComboBox, QProgressBar, QSizePolicy, QStyle, QWidget, QComboBox, QListWidgetItem, QHBoxLayout, QVBoxLayout, QTimeEdit, QAbstractSpinBox,
                             QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication, QStyleOptionComboBox, QStyleOptionMenuItem, QLabel, QLayout)

# from PySide2 import QtGui, QtCore, QtWidgets

from vidcutter.libs.graphicseffects import OpacityEffect
from vidcutter.VideoItemClip import VideoItemClip


class ClipsListWidgetItem(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.item = QListWidgetItem()
        self.widget = QWidget()
        self.comboBox = QComboBox(self)
        self.comboBox.setFixedWidth(180)
        self.checkBox = QCheckBox(self)
        self.layout1 = QHBoxLayout()
        self.layout1.addWidget(self.comboBox)
        self.layout1.setSpacing(10)
        self.layout1.addWidget(self.checkBox)

        self.startTimeLabel = QLabel("Start time")
        self.timeStart = QTimeEdit(self)
        self.timeStart.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.timeStart.setDisplayFormat('hh:mm:ss.zzz')
        self.timeStart.setFixedWidth(95)

        self.endTimeLabel = QLabel("End time")
        self.timeEnd = QTimeEdit(self)
        self.timeEnd.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.timeEnd.setDisplayFormat('hh:mm:ss.zzz')
        self.timeEnd.setFixedWidth(95)

        self.layoutTime = QVBoxLayout()
        self.layoutTime.addWidget(self.startTimeLabel, 0, Qt.AlignLeft)
        self.layoutTime.addWidget(self.timeStart, 0, Qt.AlignLeft)
        self.layoutTime.addWidget(self.endTimeLabel, 0, Qt.AlignLeft)
        self.layoutTime.addWidget(self.timeEnd, 0, Qt.AlignLeft)

        self.pixmap = QPixmap()
        self.image_label = QLabel()
        self.image_label.setPixmap(self.pixmap)
        self.layout2 = QHBoxLayout()
        self.layout2.addWidget(self.image_label)
        self.layout2.addLayout(self.layoutTime)

        self.layoutGlobal = QVBoxLayout()
        self.layoutGlobal.addLayout(self.layout1)
        self.layoutGlobal.addLayout(self.layout2)

        self.layoutGlobal.setSizeConstraint(QLayout.SetFixedSize)
        self.widget.setLayout(self.layoutGlobal)

    def on_checkBoxClicked(self):
        print('!!!')

    def setComboBoxItems(self, items: list[str]) -> None:
        self.comboBox.addItems(items)

    def setVisibility(self, checked: bool):
        self.checkBox.setChecked(checked)

    def setThumbnail(self, pixmap: QPixmap):
        self.pixmap = pixmap.scaled(QSize(100, 100), Qt.KeepAspectRatio)
        self.image_label.setPixmap(self.pixmap)

    def setTimeStart(self, timeStart: QTime):
        self.timeStart.setTime(timeStart)

    def setTimeEnd(self, timeEnd: QTime):
        self.timeEnd.setTime(timeEnd)


class VideoClipsListWidget(QListWidget):
    def __init__(self, parent=None):
        super(VideoClipsListWidget, self).__init__(parent)
        # self.itemClicked.connect(self.on_item_clicked)
        self.parent = parent
        self.theme = self.parent.theme
        self._progressBars = []
        self.setMouseTracking(True)
        self.setDropIndicatorShown(True)
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

    def renderClips(self, videoClipItems: list) -> None:
        workout_classes = ['Squat with V grip', 'Leg Press', 'Seated Cable Row', 'Barbell Bench Press', 'Rope Tricep Pushdown', 'Squats']
        self.clipsHasRendered = False
        self.clear()

        for itemIndex, videoClip in enumerate(videoClipItems):
            briefInfo = 'Here should ba a tooltip'
            listItem = ClipsListWidgetItem()
            listItem.setToolTip(briefInfo)
            listItem.setComboBoxItems(workout_classes)
            listItem.setVisibility(videoClip.visibility)
            listItem.setThumbnail(videoClip.thumbnail)
            listItem.setTimeStart(videoClip.timeStart)
            listItem.setTimeEnd(videoClip.timeEnd)

            listItem.checkBox.stateChanged.connect(lambda state, index=itemIndex: self.checkBoxStateChanged(state, index))
            listItem.timeStart.timeChanged.connect(lambda time, index=itemIndex: self.timeStartChanged(time, index))
            listItem.timeEnd.timeChanged.connect(lambda time, index=itemIndex: self.endTimeChanged(time, index))
            self.addItem(listItem.item)
            self.setItemWidget(listItem.item, listItem.widget)
            self.parent.videoSlider.addRegion(videoClip.timeStart.msecsSinceStartOfDay(), videoClip.timeEnd.msecsSinceStartOfDay(), videoClip.visibility)
        self.clipsHasRendered = True

    def checkBoxStateChanged(self, state, clipIndex: int):
        indexVideo = self.parent.videoList.currentVideoIndex
        self.parent.videoList[indexVideo].clips[clipIndex].visibility = state
        self.parent.videoSlider.setRegionVizivility(clipIndex, state)

    def timeStartChanged(self, time, index):
        print('startTimeChanged', time, index)

    def timeEndChanged(self, time, index):
        print('endTimeChanged', time, index)

    def showProgress(self, steps: int) -> None:
        for row in range(self.count()):
            item = self.item(row)
            progress = ListProgress(steps, self.visualItemRect(item), self)
            self._progressBars.append(progress)

    @pyqtSlot()
    @pyqtSlot(int)
    def updateProgress(self, item: int=None) -> None:
        if self.count():
            if item is None:
                [progress.setValue(progress.value() + 1) for progress in self._progressBars]
            else:
                self._progressBars[item].setValue(self._progressBars[item].value() + 1)

    @pyqtSlot()
    def clearProgress(self) -> None:
        for progress in self._progressBars:
            progress.hide()
            progress.deleteLater()
        self._progressBars.clear()

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

    # def resizeEvent(self, event: QResizeEvent) -> None:
    #     self.setFixedWidth(210 if self.verticalScrollBar().isVisible() else 190)
    #     self.parent.listheader.setFixedWidth(self.width())

    def clearSelection(self) -> None:
        # self.parent.seekSlider.selectRegion(-1)
        self.parent.removeItemAction.setEnabled(False)
        super(VideoClipsListWidget, self).clearSelection()


class VideoClipItemStyle(QStyledItemDelegate):
    def __init__(self, parent: VideoClipsListWidget=None):
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

    def clipText(self, text: str, painter: QPainter, chapter: bool=False) -> str:
        metrics = painter.fontMetrics()
        return metrics.elidedText(text, Qt.ElideRight, (self.parent.width() - 10 if chapter else 100 - 10))

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(220, 150)


class ListProgress(QProgressBar):
    def __init__(self, steps: int, geometry: QRect, parent=None):
        super(ListProgress, self).__init__(parent)
        self.setStyle(QStyleFactory.create('Fusion'))
        self.setRange(0, steps)
        self.setValue(0)
        self.setGeometry(geometry)
        palette = self.palette()
        palette.setColor(QPalette.Highlight, QColor(100, 44, 104))
        self.setPalette(palette)
        self.show()
