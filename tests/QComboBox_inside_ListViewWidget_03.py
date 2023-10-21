import os

from PyQt5.QtWidgets import QStyledItemDelegate, QComboBox, QApplication, QListView, QListWidget, QStyle
from PyQt5.QtCore import QAbstractListModel, Qt, QRect, QSize
from PyQt5.QtGui import QColor, QFont, QIcon
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QComboBox, QProgressBar, QSizePolicy, QStyle,
                             QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication, QStyleOptionComboBox, QStyleOptionMenuItem)

import PySide2
import PyQt5.QtGui as QtGui

class QBDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        value = index.data(Qt.EditRole)
        if isinstance(value, PlainList):
            comboBox = QComboBox(parent)
            comboBox.setModel(value)
            comboBox.setCurrentIndex(value.currentIndex)
            # submit the data whenever the index changes
            comboBox.currentIndexChanged.connect(lambda: self.commitData.emit(comboBox))
        else:
            comboBox = super().createEditor(parent, option, index)
        return comboBox

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            # the default implementation tries to set the text if the
            # editor is a combobox, but we need to set the index
            model.setData(index, editor.currentIndex())
        else:
            super().setModelData(editor, model, index)

    def paint(self, painter, option, index):
        super(QBDelegate, self).paint(painter, option, index)
        title = 'Just title'  # index.data(TitleRole)
        icon = QIcon('checker.png')  # index.data(IconRole)

        mode = QIcon.Normal
        if not (option.state & QStyle.State_Enabled):
            mode = QIcon.Disabled
        elif option.state & QStyle.State_Selected:
            mode = QIcon.Selected

        state = (QIcon.On if option.state & QStyle.State_Open else QIcon.Off)

        iconRect = QRect(option.rect)
        iconRect.setSize(QSize(40, 40))
        icon.paint(painter, iconRect, Qt.AlignLeft | Qt.AlignVCenter, mode, state)


class PlainList(QAbstractListModel):
    currentIndex = 0

    def __init__(self, elements):
        super().__init__()
        self.elements = []
        for element in elements:
            if isinstance(element, (tuple, list)) and element:
                element = PlainList(element)
            self.elements.append(element)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.EditRole:
            return self.elements[index.row()]
        elif role == Qt.DisplayRole:
            value = self.elements[index.row()]
            if isinstance(value, PlainList):
                return value.elements[value.currentIndex]
            else:
                return value

    def flags(self, index):
        flags = super().flags(index)
        if isinstance(index.data(Qt.EditRole), PlainList):
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            item = self.elements[index.row()]
            if isinstance(item, PlainList):
                item.currentIndex = value
            else:
                self.elements[index.row()] = value
        return True

    def rowCount(self, parent=None):
        return len(self.elements)



app = QApplication([])

qb0 = 'powdered sugar'  # no other choice
qb1 = ['whole milk', '2% milk', 'half-and-half']
qb2 = ['butter', 'lard']
qb3 = 'cayenne pepper'  # there is no substitute

QV = QListView()
qlist = PlainList([qb0, qb1, qb2, qb3])

QV.setModel(qlist)
QV.setItemDelegate(QBDelegate(QV))

## to always display the combo:
# for i in range(qlist.rowCount()):
#    index = qlist.index(i)
#    if index.flags() & Qt.ItemIsEditable:
#        QV.openPersistentEditor(index)

QV.show()

app.exec_()