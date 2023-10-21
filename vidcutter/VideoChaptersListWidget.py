#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import sys
import copy

from PyQt5.QtCore import pyqtSlot, Qt, QEvent, QModelIndex, QRect, QSize, QTime, QPoint
from PyQt5.QtGui import QColor, QFont, QIcon, QMouseEvent, QPainter, QPalette, QPen, QResizeEvent, QContextMenuEvent
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QComboBox, QProgressBar, QSizePolicy, QStyle,
                             QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication, QStyleOptionComboBox, QStyleOptionMenuItem)

# from PySide2 import QtGui, QtCore, QtWidgets

from vidcutter.libs.graphicseffects import OpacityEffect
from vidcutter.VideoItemClip import VideoItemClip

'''
class ComboBoxDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent=None):
        super(ComboBoxDelegate, self).__init__(parent)
        self.items = []

    def setItems(self, items):
        self.items = items

    def createEditor(self, widget, option, index):
        editor = QtGui.QComboBox(widget)
        editor.addItems(self.items)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        if value:
            editor.setCurrentIndex(int(value))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentIndex(), QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def paint(self, painter, option, index):
        text = self.items[index.row()]
        option.text = text
        QtGui.QApplication.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter)
'''



class VideoClipsListWidget(QListWidget):
    def __init__(self, parent=None):
        super(VideoClipsListWidget, self).__init__(parent)
        # self.itemClicked.connect(self.on_item_clicked)
        self.parent = parent
        self.theme = self.parent.theme
        self._progressBars = []
        self.setMouseTracking(True)
        self.setDropIndicatorShown(True)
        self.setFixedWidth(190)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setItemDelegate(VideoClipItemStyle(self))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
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


    def mousePressEvent(self, event):
        self._mouseButton = event.button()
        super(VideoClipsListWidget, self).mousePressEvent(event)

    def renderClips(self, videoClipItems: list) -> None:
        self.clipsHasRendered = False
        self.clear()
        for index, videoClip in enumerate(videoClipItems):
            listItem = QListWidgetItem(self)
            listItem.setToolTip('Drag to reorder clips')
            endItem = videoClip.timeEnd.toString(self.parent.runtimeformat)
            listItem.setStatusTip('Reorder clips with mouse drag & drop or right-click menu on the clip to be moved')
            listItem.setTextAlignment(Qt.AlignVCenter)
            listItem.setData(Qt.DecorationRole + 1, videoClip.thumbnail)
            listItem.setData(Qt.DisplayRole + 1, videoClip.timeStart.toString(self.parent.runtimeformat))
            listItem.setData(Qt.UserRole + 1, endItem)
            listItem.setData(Qt.UserRole + 2, videoClip.description)
            listItem.setData(Qt.UserRole + 3, videoClip.name)
            listItem.setData(Qt.UserRole + 4, ['Barbel Row', 'Other'])
            listItem.setData(Qt.CheckStateRole, videoClip.visibility)
            listItem.setCheckState(videoClip.visibility)
            listItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            self.addItem(listItem)
            self.parent.videoSlider.addRegion(videoClip.timeStart.msecsSinceStartOfDay(), videoClip.timeEnd.msecsSinceStartOfDay(), videoClip.visibility)
        self.clipsHasRendered = True

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

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.setFixedWidth(210 if self.verticalScrollBar().isVisible() else 190)
        # self.parent.listheader.setFixedWidth(self.width())

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
        r = option.rect
        penColor = Qt.white if self.theme == 'dark' else Qt.black
        if self.parent.isEnabled():
            if option.state & QStyle.State_Selected:
                painter.setBrush(QColor(150, 78, 190, 200))
            elif option.state & QStyle.State_MouseOver:
                painter.setBrush(QColor(227, 212, 232, 150))
                penColor = Qt.black
            else:
                brushcolor = QColor(79, 85, 87, 150) if self.theme == 'dark' else QColor('#EFF0F1')
                painter.setBrush(Qt.transparent if index.row() % 2 == 0 else brushcolor)
        painter.setPen(Qt.NoPen)
        painter.drawRect(r)
        thumbnailIcon = QIcon(index.data(Qt.DecorationRole + 1))
        startTime = index.data(Qt.DisplayRole + 1)
        endTime = index.data(Qt.UserRole + 1)
        comboBoxClasses = index.data(Qt.UserRole + 4)

        optionComboBox = QStyleOptionComboBox()
        optionComboBox.QStyleOption = option
        optionComboBox.rect = option.rect.adjusted(3, 5, -44, -78)
        optionComboBox.editable = True
        optionComboBox.currentText = comboBoxClasses[0]
        # optionComboBox.SO_MenuItem. subControls.SC_ComboBoxListBoxPopup

        optionChecker = QStyleOptionButton()
        optionChecker.QStyleOption = option
        checker_rect = QApplication.style().subElementRect(QStyle.SE_ViewItemCheckIndicator, optionChecker)
        optionChecker.rect = option.rect.adjusted(165, -85, checker_rect.width(), checker_rect.height())
        is_checked = bool(index.data(Qt.CheckStateRole))

        if is_checked:
            optionChecker.state |= QStyle.State_On
        else:
            optionChecker.state |= QStyle.State_Off

        painter.setPen(QPen(penColor, 1, Qt.SolidLine))
        '''
        if len(chapterName):
            offset = 20
            r = option.rect.adjusted(5, 5, 0, 0)
            cfont = QFont('Futura LT', -1, QFont.Medium)
            cfont.setPointSizeF(12.25 if sys.platform == 'darwin' else 10.25)
            painter.setFont(cfont)
            painter.drawText(r, Qt.AlignLeft, self.clipText(chapterName, painter, True))
            r = option.rect.adjusted(5, offset, 0, 0)
        else:
            offset = 0
            r = option.rect.adjusted(5, 0, 0, 0)
        '''

        offset = 20
        r = option.rect.adjusted(5, 5, -5, -5)
        thumbnailIcon.paint(painter, r, Qt.AlignBottom | Qt.AlignLeft)

        r = option.rect.adjusted(110, 10 + offset, 0, 0)
        painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Bold))
        painter.drawText(r, Qt.AlignLeft, 'START')
        r = option.rect.adjusted(110, 23 + offset, 0, 0)
        painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Normal))
        painter.drawText(r, Qt.AlignLeft, startTime)
        if len(endTime) > 0:
            r = option.rect.adjusted(110, 48 + offset, 0, 0)
            painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Bold))
            painter.drawText(r, Qt.AlignLeft, 'END')
            r = option.rect.adjusted(110, 60 + offset, 0, 0)
            painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Normal))
            painter.drawText(r, Qt.AlignLeft, endTime)

        QApplication.style().drawControl(QStyle.CE_CheckBox, optionChecker, painter)
        QApplication.style().drawComplexControl(QStyle.CC_ComboBox, optionComboBox, painter)

    def clipText(self, text: str, painter: QPainter, chapter: bool=False) -> str:
        metrics = painter.fontMetrics()
        return metrics.elidedText(text, Qt.ElideRight, (self.parent.width() - 10 if chapter else 100 - 10))

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(185, 105 if self.parent.parent.createChapters else 85)


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
