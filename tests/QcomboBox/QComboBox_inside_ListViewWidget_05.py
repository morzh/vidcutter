from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor, QFont, QIcon
from PyQt5.QtWidgets import QStyledItemDelegate, QComboBox, QApplication, QListView, QListWidget, QStyle, QItemDelegate
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem, QComboBox, QProgressBar, QSizePolicy, QStyle, QVBoxLayout, QTimeEdit,
                             QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QCheckBox, QStyleOptionButton, QApplication, QStyleOptionComboBox, QStyleOptionMenuItem)



app = QApplication([])

item1 = QtWidgets.QListWidgetItem()
# Create widget
widget1 = QtWidgets.QWidget()
widgetText1 = QtWidgets.QLabel("I love PyQt!")
widgetComboBox = QtWidgets.QComboBox()
widgetComboBox.addItems(['001', '002', '003'])
widgetLayout1 = QtWidgets.QHBoxLayout()
widgetLayout1.addWidget(widgetText1)
widgetLayout1.addWidget(widgetComboBox)

widgetLayout1.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
widget1.setLayout(widgetLayout1)
item1.setSizeHint(widget1.sizeHint())


itemN = QtWidgets.QListWidgetItem()
# Create widget
widget = QtWidgets.QWidget()
widgetText = QtWidgets.QLabel("I love PyQt!")
widgetButton = QtWidgets.QComboBox()
widgetButton.addItems(['001', '002', '003'])
widgetLayout = QtWidgets.QHBoxLayout()
widgetLayout.addWidget(widgetText)
widgetLayout.addWidget(widgetButton)
widgetLayout.addStretch()

widgetLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
widget.setLayout(widgetLayout)
itemN.setSizeHint(widget.sizeHint())


funList = QListWidget()
funList.addItem(item1)
funList.addItem(itemN)
funList.setItemWidget(item1, widget1)
funList.setItemWidget(itemN, widget)
funList.show()

app.exec_()

