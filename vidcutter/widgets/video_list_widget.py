import sys

from PyQt5.QtCore import Qt, QModelIndex, QSize
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPainterPath
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QSizePolicy, QStyle, QStyledItemDelegate, QStyleOptionViewItem)

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
        self.setFixedWidth(165)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setItemDelegate(VideoListItemStyle(self))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setUniformItemSizes(True)
        self.setDragEnabled(False)
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

    def renderList(self, video_list) -> None:
        self.clear()
        for index, video in enumerate(video_list.videos):
            list_item = QListWidgetItem(self)
            tooltip_string = ''.join(['FILENAME: \n', video.filename, '\n',
                                      'DURATION:\n', video.duration.toString(self.parent.timeformat), '\n',
                                      '----------------------------------------\n',
                                      'Double click to load video'])
            list_item.setToolTip(tooltip_string)
            list_item.setStatusTip('Reorder clips with mouse drag & drop or right-click menu on the clip to be moved')
            list_item.setTextAlignment(Qt.AlignVCenter)
            list_item.setData(Qt.DecorationRole + 1, video.thumbnail)
            list_item.setData(Qt.UserRole + 1, index + 1)
            # list_item.setData(Qt.UserRole + 2, video.duration.toString(self.parent.timeformat))
            list_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.addItem(list_item)

        self.videosHasRendered = True


class VideoListItemStyle(QStyledItemDelegate):
    def __init__(self, parent: VideoListWidget=None):
        super(VideoListItemStyle, self).__init__(parent)
        self.parent = parent
        self.theme = self.parent.theme

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
        pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio)
        pixmap = self.roundedPixmap(pixmap, 12)
        thumbnail_icon = QIcon(pixmap)
        video_index = str(index.data(Qt.UserRole + 1))

        painter.setPen(QPen(pencolor, 1, Qt.SolidLine))
        r = option.rect.adjusted(5, 5, -5, -5)
        thumbnail_icon.paint(painter, r, Qt.AlignTop | Qt.AlignRight)

        r = option.rect.adjusted(15, 0, 0, 0)
        painter.setFont(QFont('Arial', 13 if sys.platform == 'darwin' else 11, QFont.Bold))
        painter.drawText(r, Qt.AlignLeft | Qt.AlignVCenter, video_index)


    def clipText(self, text: str, painter: QPainter, chapter: bool=False) -> str:
        metrics = painter.fontMetrics()
        return metrics.elidedText(text, Qt.ElideRight, (self.parent.width() - 10 if chapter else 100 - 10))

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(80, 80)

