import logging
import sys
from datetime import datetime

from PyQt5.Qt import PYQT_VERSION_STR
from PyQt5.QtCore import QFile, QObject, QSize, QTextStream, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QStyleFactory,
                             QTabWidget, QVBoxLayout, QWidget, QTextEdit, QTableWidget, QTableWidgetItem, qApp)

from vidcutter.libs.config import cached_property
import vidcutter


class VideoDescriptionDialog(QDialog):
    def __init__(self, parent: QWidget):
        super(VideoDescriptionDialog, self).__init__(parent)
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        self.theme = self.parent.theme
        self.setContentsMargins(0, 0, 0, 0)
        self.setWindowFlags(Qt.Window | Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowModality(Qt.ApplicationModal)

        title = 'Edit Video Description'
        self.layout = QVBoxLayout()
        self.buttonsLayout = QHBoxLayout()
        self.descriptionLayout = QHBoxLayout()
        self.descriptionLayout.setSpacing(3)

        self.textField = QTextEdit()

        self.issuesTable = QTableWidget()
        self.issuesTable.setRowCount(5)
        self.issuesTable.setColumnCount(1)
        self.issuesTable.verticalHeader().setVisible(False)
        self.issuesTable.horizontalHeader().setVisible(False)
        self.addIssuesItems()

        self.descriptionLayout.addWidget(self.textField)
        self.descriptionLayout.addWidget(self.issuesTable)

        # self.acceptButton = QDialogButtonBox
        # self.buttonsLayout.addWidget()
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.layout.addLayout(self.descriptionLayout)
        self.layout.addWidget(self.buttonBox)

        self.setLayout(self.layout)
        self.setWindowTitle(title)

    def addIssuesItems(self):
        for idx in range(5):
            chkBoxItem = QTableWidgetItem()
            chkBoxItem.setText('string')
            chkBoxItem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chkBoxItem.setCheckState(Qt.Unchecked)
            self.issuesTable.setItem(idx, 0, chkBoxItem)
