import os
import sys
import copy

from PyQt5.QtCore import pyqtSlot, Qt, QEvent, QModelIndex, QRect, QSize, QTime, QPoint
from PyQt5.QtGui import QColor, QFont, QIcon, QMouseEvent, QPainter, QPalette, QPen, QResizeEvent, QContextMenuEvent
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QProgressBar, QSizePolicy, QStyle,
                             QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication)

# import PyQt5.QtCore.

from vidcutter.libs.graphicseffects import OpacityEffect


class VideoListWidget(QListWidget):
    def __init__(self, parent=None):
        super(VideoListWidget, self).__init__(parent)
        # self.itemClicked.connect(self.on_item_clicked)
        self.parent = parent
        self.theme = self.parent.theme
        self._progressbars = []
        self.setMouseTracking(True)
        self.setDropIndicatorShown(True)
        self.setFixedWidth(190)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setItemDelegate(VideoListItemStyle(self))
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
        self.videosHasRendered = False

    def renderList(self, videoList) -> None:
        self.clear()
        for video in videoList.videos:
            listitem = QListWidgetItem(self)
            listitem.setToolTip(video.filename)
            listitem.setStatusTip('Reorder clips with mouse drag & drop or right-click menu on the clip to be moved')
            listitem.setTextAlignment(Qt.AlignVCenter)
            listitem.setData(Qt.DecorationRole + 1, video.thumbnail)
            listitem.setData(Qt.UserRole + 1, video.filename)
            listitem.setData(Qt.UserRole + 2, video.duration.toString(self.parent.timeformat))
            listitem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.addItem(listitem)

        self.videosHasRendered = True

class VideoListItemStyle(QStyledItemDelegate):

    def __init__(self, parent: VideoListWidget=None):
        super(VideoListItemStyle, self).__init__(parent)
        self.parent = parent
        self.theme = self.parent.theme

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        r = option.rect
        pencolor = Qt.white if self.theme == 'dark' else Qt.black
        if self.parent.isEnabled():
            if option.state & QStyle.State_Selected:
                painter.setBrush(QColor(150, 190, 78, 210))
            elif option.state & QStyle.State_MouseOver:
                painter.setBrush(QColor(227, 212, 232, 150))
                pencolor = Qt.black
            else:
                brushcolor = QColor(49, 45, 47, 175) if self.theme == 'dark' else QColor('#EFF0F1')
                painter.setBrush(Qt.transparent if index.row() % 2 == 0 else brushcolor)
        painter.setPen(Qt.NoPen)
        painter.drawRect(r)

        pixmap = index.data(Qt.DecorationRole + 1)
        thumbnailIcon = QIcon(pixmap)
        filename = index.data(Qt.UserRole + 1)
        duration = index.data(Qt.UserRole + 2)

        painter.setPen(QPen(pencolor, 1, Qt.SolidLine))
        r = option.rect.adjusted(0, 0, -20, -20)
        thumbnailIcon.paint(painter, r, Qt.AlignTop | Qt.AlignLeft)

        r = option.rect.adjusted(90, 10, 0, 0)
        painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Bold))
        painter.drawText(r, Qt.AlignLeft, 'DURATION:')
        r = option.rect.adjusted(90, 30, 0, 0)
        cfont = QFont('Futura LT', 8, QFont.Medium)
        painter.setFont(cfont)
        painter.drawText(r, Qt.AlignLeft, duration)

        r = option.rect.adjusted(90, 70, 0, 0)
        painter.setFont(QFont('Noto Sans', 11 if sys.platform == 'darwin' else 9, QFont.Bold))
        painter.drawText(r, Qt.AlignLeft, 'FILE NAME:')

        if len(filename):
            r = option.rect.adjusted(5, 85, 0, 0)
            cfont = QFont('Futura LT', -1, QFont.Medium)
            cfont.setPointSizeF(11 if sys.platform == 'darwin' else 10)
            painter.setFont(cfont)
            painter.drawText(r, Qt.AlignLeft, self.clipText(filename, painter, True))

    def clipText(self, text: str, painter: QPainter, chapter: bool=False) -> str:
        metrics = painter.fontMetrics()
        return metrics.elidedText(text, Qt.ElideRight, (self.parent.width() - 10 if chapter else 100 - 10))

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(105, 105)

