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

import os
import sys
import copy

from PyQt5.QtCore import pyqtSlot, Qt, QEvent, QModelIndex, QRect, QSize, QTime, QPoint
from PyQt5.QtGui import QColor, QFont, QIcon, QMouseEvent, QPainter, QPalette, QPen, QResizeEvent, QContextMenuEvent
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QProgressBar, QSizePolicy, QStyle,
                             QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication)

# import PyQt5.QtCore.

from vidcutter.libs.graphicseffects import OpacityEffect
from vidcutter.VideoItemClip import VideoItemClip


class VideoClipsListWidget(QListWidget):
    def __init__(self, parent=None):
        super(VideoClipsListWidget, self).__init__(parent)
        # self.itemClicked.connect(self.on_item_clicked)
        self.parent = parent
        self.theme = self.parent.theme
        self._progressbars = []
        self.setMouseTracking(True)
        self.setDropIndicatorShown(True)
        self.setFixedWidth(190)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setItemDelegate(VideoClipItemStyle(self))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setUniformItemSizes(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAlternatingRowColors(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setObjectName('cliplist')
        self.setStyleSheet('QListView::item { border: none; }')
        self.opacityEffect = OpacityEffect(0.3)
        self.opacityEffect.setEnabled(False)
        self.setGraphicsEffect(self.opacityEffect)
        self.clips_has_rendered = False

    def mousePressEvent(self, event):
        self._mouse_button = event.button()
        super(VideoClipsListWidget, self).mousePressEvent(event)

    def renderClips(self, video_clip_items: list) -> None:
        self.clips_has_rendered = False
        self.clear()
        for index, videoClip in enumerate(video_clip_items):
            list_item = QListWidgetItem(self)
            list_item.setToolTip('Drag to reorder clips')
            end_item = videoClip.timeEnd.toString(self.parent.runtimeformat)
            list_item.setStatusTip('Reorder clips with mouse drag & drop or right-click menu on the clip to be moved')
            list_item.setTextAlignment(Qt.AlignVCenter)
            list_item.setData(Qt.DecorationRole + 1, videoClip.thumbnail)
            list_item.setData(Qt.DisplayRole + 1, videoClip.timeStart.toString(self.parent.runtimeformat))
            list_item.setData(Qt.UserRole + 1, end_item)
            list_item.setData(Qt.UserRole + 2, videoClip.description)
            list_item.setData(Qt.UserRole + 3, videoClip.name)
            list_item.setData(Qt.CheckStateRole, videoClip.visibility)
            list_item.setCheckState(videoClip.visibility)
            list_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            self.addItem(list_item)
            self.parent.videoSlider.addRegion(videoClip.timeStart.msecsSinceStartOfDay(), videoClip.timeEnd.msecsSinceStartOfDay(), videoClip.visibility)
        self.clips_has_rendered = True

    def showProgress(self, steps: int) -> None:
        for row in range(self.count()):
            item = self.item(row)
            progress = ListProgress(steps, self.visualItemRect(item), self)
            self._progressbars.append(progress)

    @pyqtSlot()
    @pyqtSlot(int)
    def updateProgress(self, item: int=None) -> None:
        if self.count():
            if item is None:
                [progress.setValue(progress.value() + 1) for progress in self._progressbars]
            else:
                self._progressbars[item].setValue(self._progressbars[item].value() + 1)

    @pyqtSlot()
    def clearProgress(self) -> None:
        for progress in self._progressbars:
            progress.hide()
            progress.deleteLater()
        self._progressbars.clear()

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
        opt_button = QStyleOptionButton()
        opt_button.QStyleOption = option
        checker_rect = QApplication.style().subElementRect(QStyle.SE_ViewItemCheckIndicator, opt_button)
        return option.rect.adjusted(165, -85, checker_rect.width(), checker_rect.height())

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        r = option.rect
        pencolor = Qt.white if self.theme == 'dark' else Qt.black
        if self.parent.isEnabled():
            if option.state & QStyle.State_Selected:
                painter.setBrush(QColor(150, 78, 190, 200))
            elif option.state & QStyle.State_MouseOver:
                painter.setBrush(QColor(227, 212, 232, 150))
                pencolor = Qt.black
            else:
                brushcolor = QColor(79, 85, 87, 150) if self.theme == 'dark' else QColor('#EFF0F1')
                painter.setBrush(Qt.transparent if index.row() % 2 == 0 else brushcolor)
        painter.setPen(Qt.NoPen)
        painter.drawRect(r)
        thumbicon = QIcon(index.data(Qt.DecorationRole + 1))
        starttime = index.data(Qt.DisplayRole + 1)
        endtime = index.data(Qt.UserRole + 1)
        externalPath = index.data(Qt.UserRole + 2)
        chapterName = index.data(Qt.UserRole + 3)

        cbOpt = QStyleOptionButton()
        cbOpt.QStyleOption = option
        checker_rect = QApplication.style().subElementRect(QStyle.SE_ViewItemCheckIndicator, cbOpt)
        cbOpt.rect = option.rect.adjusted(165, -85, checker_rect.width(), checker_rect.height())
        isChecked = bool(index.data(Qt.CheckStateRole))

        if isChecked:
            cbOpt.state |= QStyle.State_On
        else:
            cbOpt.state |= QStyle.State_Off

        painter.setPen(QPen(pencolor, 1, Qt.SolidLine))
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

        thumbicon.paint(painter, r, Qt.AlignVCenter | Qt.AlignLeft)

        r = option.rect.adjusted(110, 10 + offset, 0, 0)
        painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Bold))
        painter.drawText(r, Qt.AlignLeft, 'FILENAME' if len(externalPath) else 'START')
        r = option.rect.adjusted(110, 23 + offset, 0, 0)
        painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Normal))
        if len(externalPath):
            painter.drawText(r, Qt.AlignLeft, self.clipText(os.path.basename(externalPath), painter))
        else:
            painter.drawText(r, Qt.AlignLeft, starttime)
        if len(endtime) > 0:
            r = option.rect.adjusted(110, 48 + offset, 0, 0)
            painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Bold))
            painter.drawText(r, Qt.AlignLeft, 'RUNTIME' if len(externalPath) else 'END')
            r = option.rect.adjusted(110, 60 + offset, 0, 0)
            painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Normal))
            painter.drawText(r, Qt.AlignLeft, endtime)

        QApplication.style().drawControl(QStyle.CE_CheckBox, cbOpt, painter)

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
