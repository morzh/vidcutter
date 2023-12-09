# import sip
# sip.setapi('QString', 2)
# sip.setapi('QVariant', 2)


import PyQt5
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QStyledItemDelegate, QComboBox, QApplication, QListView, QListWidget, QStyle, QItemDelegate, QStyleOptionComboBox

class TableModel(QtCore.QAbstractTableModel):
    """
    A simple 5x4 table data_model to demonstrate the delegates
    """
    def rowCount(self, parent=QtCore.QModelIndex()): return 5
    def columnCount(self, parent=QtCore.QModelIndex()): return 4

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid(): return None
        if not role==QtCore.Qt.DisplayRole: return None
        return "{0:02d}".format(index.row())


class ComboDelegate(QItemDelegate):
    """
    A delegate that places a fully functioning QComboBox in every
    cell of the column to which it's applied
    """
    def __init__(self, parent):
        QItemDelegate.__init__(self, parent)

    def paint(self, painter, option, index):
        rectangle = option.rect

        self.combo = PyQt5.QtWidgets.QComboBox(self.parent())
        self.combo.currentIndexChanged.connect(lambda: self.commitData.emit(self.combo))
        # self.connect(self.combo, QtCore.SIGNAL("currentIndexChanged(int)"), self.parent().currentIndexChanged)
        style = self.combo.style()
        li = ["Zero", "One", "Two", "Three", "Four", "Five"]
        self.combo.setFixedWidth(55)
        self.combo.setFixedHeight(20)
        self.combo.addItems(li)

        optionComboBox = QStyleOptionComboBox()
        optionComboBox.state = option.state
        optionComboBox.QStyleOption = option
        optionComboBox.state |= QStyle.State_Enabled
        optionComboBox.rect = rectangle.adjusted(5, 5, -5, -5)

        style.drawComplexControl(QStyle.CC_ComboBox, optionComboBox, painter)
        style.drawControl(QStyle.CE_ComboBoxLabel, optionComboBox, painter)

        if not self.parent().indexWidget(index):
            self.parent().setIndexWidget(index, self.combo)


class TableView(PyQt5.QtWidgets.QTableView):
    """
    A simple table to demonstrate the QComboBox delegate.
    """
    def __init__(self, *args, **kwargs):
        PyQt5.QtWidgets.QTableView.__init__(self, *args, **kwargs)

        # Set the delegate for column 0 of our table
        # self.setItemDelegateForColumn(0, ButtonDelegate(self))
        self.setItemDelegateForColumn(0, ComboDelegate(self))

    @QtCore.pyqtSlot()
    def currentIndexChanged(self, ind):
        print( "Combo Index changed {0} {1} : {2}".format(ind, self.sender().currentIndex(), self.sender().currentText()))


if __name__=="__main__":
    from sys import argv, exit

    class Widget(PyQt5.QtWidgets.QWidget):
        """
        A simple test widget to contain and own the data_model and table.
        """
        def __init__(self, parent=None):
            PyQt5.QtWidgets.QWidget.__init__(self, parent)

            l=PyQt5.QtWidgets.QVBoxLayout(self)
            self._tm=TableModel(self)
            self._tv=TableView(self)
            self._tv.setModel(self._tm)
            l.addWidget(self._tv)


    a = QApplication([])
    w=Widget()
    w.show()
    w.raise_()
    exit(a.exec_())