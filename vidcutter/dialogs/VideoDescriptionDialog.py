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
    def __init__(self, parent: QWidget, issuesList, checkedIssues, description):
        super(VideoDescriptionDialog, self).__init__(parent)
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        self.theme = self.parent.theme
        self.setContentsMargins(0, 0, 0, 0)
        self.setWindowFlags(Qt.Window | Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.issuesList = issuesList

        title = 'Edit Video Description'
        self.layout = QVBoxLayout()
        self.buttonsLayout = QHBoxLayout()
        self.descriptionLayout = QHBoxLayout()
        self.descriptionLayout.setSpacing(3)

        self.textField = QTextEdit()
        self.textField.setText(description)

        self.issuesTable = QTableWidget()
        self.issuesTable.setRowCount(len(self.issuesList))
        self.issuesTable.adjustSize()
        self.issuesTable.setColumnCount(1)
        self.issuesTable.verticalHeader().setVisible(False)
        self.issuesTable.horizontalHeader().setVisible(False)
        self.addIssuestableItems(checkedIssues)

        self.descriptionLayout.addWidget(self.issuesTable)
        self.descriptionLayout.addWidget(self.textField)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.layout.addLayout(self.descriptionLayout)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)
        self.setWindowTitle(title)

    def addIssuestableItems(self, checked_issues):
        self.issuesTable.horizontalHeader().setStretchLastSection(True)
        for idx in range(len(self.issuesList)):
            chkBoxItem = QTableWidgetItem()
            chkBoxItem.setText(self.issuesList[idx])
            chkBoxItem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            if idx in checked_issues:
                chkBoxItem.setCheckState(Qt.Checked)
            else:
                chkBoxItem.setCheckState(Qt.Unchecked)
            self.issuesTable.setItem(idx, 0, chkBoxItem)
