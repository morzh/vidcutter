import os
import sys
import copy

from PyQt5.QtCore import pyqtSlot, Qt, QEvent, QModelIndex, QRect, QSize, QTime, QPoint
from PyQt5.QtGui import QColor, QFont, QIcon, QMouseEvent, QPainter, QPalette, QPen, QResizeEvent, QContextMenuEvent
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QProgressBar, QSizePolicy, QStyle,
                             QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication)

# import PyQt5.QtCore.

from vidcutter.libs.graphicseffects import OpacityEffect

class VideosList(QListWidget):
    def __init__(self, parent=None):
        super(VideosList, self).__init__(parent)
        # self.itemClicked.connect(self.on_item_clicked)
        self.parent = parent
        self.theme = self.parent.theme
        self._progressbars = []
        self.setMouseTracking(True)
        self.setDropIndicatorShown(True)
        self.setFixedWidth(190)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setContentsMargins(0, 0, 0, 0)
        # self.setItemDelegate(VideoItem(self))
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
        self.clipsHasRendered = False