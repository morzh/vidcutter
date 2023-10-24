from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QTime, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap, QImage, QPainter
from PyQt5.QtWidgets import QStyledItemDelegate, QComboBox, QApplication, QListView, QListWidget, QStyle, QItemDelegate
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QComboBox, QProgressBar, QSizePolicy, QStyle, QVBoxLayout, QTimeEdit, QGraphicsView, QGraphicsPixmapItem,
                             QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication, QStyleOptionComboBox, QStyleOptionMenuItem, QLabel)


class ClipsListWidgetItem(QtWidgets.QWidget):
    def __init__(self, comboList: list[str], parent=None):
        super().__init__(parent)
        self.item = QtWidgets.QListWidgetItem()
        self.widget = QtWidgets.QWidget()
        self.comboBox = QtWidgets.QComboBox()
        self.comboBox.addItems(comboList)
        self.comboBox.setFixedWidth(160)
        self.checkBox = QCheckBox()

        self.layout1 = QtWidgets.QHBoxLayout()
        self.layout1.addWidget(self.comboBox)
        self.layout1.setSpacing(8)
        self.layout1.addWidget(self.checkBox)

        self.startTimeLabel = QtWidgets.QLabel("Start time")
        self.timeStart = QTime(10, 30)
        self.startTime = QTimeEdit(self)
        self.startTime.setDisplayFormat('hh:mm:ss')
        self.timeEnd = QTime(20, 30)
        self.endTimeLabel = QtWidgets.QLabel("End time")
        self.endTime = QTimeEdit(self)
        self.endTime.setDisplayFormat('hh:mm:ss')

        self.layoutTime = QtWidgets.QVBoxLayout()
        self.layoutTime.addWidget(self.startTimeLabel)
        self.layoutTime.addWidget(self.startTime)
        self.layoutTime.addWidget(self.endTimeLabel)
        self.layoutTime.addWidget(self.endTime)

        self.pixmap = QPixmap('checker.png')
        self.pixmap = self.pixmap.scaled(QSize(95, 95), Qt.KeepAspectRatio)
        self.image_label = QLabel()
        self.image_label.setPixmap(self.pixmap)
        self.layout2 = QtWidgets.QHBoxLayout()
        self.layout2.addWidget(self.image_label)
        self.layout2.addLayout(self.layoutTime)

        self.layoutGlobal = QVBoxLayout()
        self.layoutGlobal.addLayout(self.layout1)
        self.layoutGlobal.addLayout(self.layout2)

        self.layoutGlobal.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.widget.setLayout(self.layoutGlobal)
        # self.item.setSizeHint(widget1.sizeHint())
        self.item.setSizeHint(QSize(120, 120))


class VideoListItemStyle(QStyledItemDelegate):
    def __init__(self, parent: QListWidget=None):
        super(VideoListItemStyle, self).__init__(parent)
        self.parent = parent

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        r = option.rect
        pencolor = Qt.white
        if option.state & QStyle.State_Selected:
            painter.setBrush(QColor(150, 190, 78, 210))
        elif option.state & QStyle.State_MouseOver:
            painter.setBrush(QColor(227, 212, 232, 150))
            pencolor = Qt.black
        else:
            brushcolor = QColor(49, 45, 47, 175)
            painter.setBrush(Qt.transparent if index.row() % 2 == 0 else brushcolor)
        painter.setPen(pencolor)
        painter.drawRect(r)

    def clipText(self, text: str, painter: QPainter, chapter: bool=False) -> str:
        metrics = painter.fontMetrics()
        return metrics.elidedText(text, Qt.ElideRight, (self.parent.width() - 10 if chapter else 100 - 10))

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(150, 150)


app = QApplication([])

workout_list = ['Squat with V grip', 'Leg Press', 'Seated Cable Row', 'Barbell Bench Press', 'Rope Tricep Pushdown', 'Squats']
number_items = 5
funList = QListWidget()
funList.setFixedHeight(800)
funList.setFixedWidth(198)
funList.setItemDelegate(VideoListItemStyle(funList))
funList.viewport().setAttribute(Qt.WA_Hover)

for index in range(number_items):
    listItem = ClipsListWidgetItem(workout_list)
    funList.addItem(listItem.item)
    funList.setItemWidget(listItem.item, listItem.widget)

funList.show()

app.exec_()

