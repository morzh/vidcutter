import logging

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QVBoxLayout, QWidget, QTextEdit, QTableWidget, QTableWidgetItem)

import vidcutter.widgets.dialogs.video_info_dialog_style_sheet as styleSheet


class VideoDescriptionDialog(QDialog):
    def __init__(self, parent: QWidget, issuesList, checkedIssues, description):
        super(VideoDescriptionDialog, self).__init__(parent)
        self.issuesTableIsComplete = False
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        self.theme = self.parent.theme
        self.setContentsMargins(0, 0, 0, 0)
        self.setWindowFlags(Qt.Window | Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowModality(Qt.ApplicationModal)

        self.issuesList = issuesList
        self.checkedIssuesList = []

        title = 'Edit Video Description'
        self.layout = QVBoxLayout()
        self.buttonsLayout = QHBoxLayout()
        self.descriptionLayout = QHBoxLayout()
        self.descriptionLayout.setSpacing(3)

        self.textField = QTextEdit()
        self.textField.setText(description)

        self.issuesTable = QTableWidget()
        self.issuesTable.setRowCount(len(issuesList))
        self.issuesTable.setColumnCount(1)
        self.issuesTable.verticalHeader().setVisible(False)
        self.issuesTable.horizontalHeader().setVisible(False)
        self.issuesTable.adjustSize()
        self.issuesTable.cellChanged.connect(self.on_issuesTableChanged)
        self.addIssuestableItems(checkedIssues)

        self.descriptionLayout.addWidget(self.issuesTable)
        self.descriptionLayout.addWidget(self.textField)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.layout.addLayout(self.descriptionLayout)
        self.layout.addWidget(self.buttons)

        self.setMaximumSize(QSize(600, 500))
        self.setMinimumSize(QSize(400, 500))

        self.setLayout(self.layout)
        self.setWindowTitle(title)

        if parent.theme == 'dark':
            self.setStyleSheet(styleSheet.video_info_style_sheet_dark)
        else:
            self.setStyleSheet(styleSheet.video_info_style_sheet_light)

    def addIssuestableItems(self, checked_issues):
        self.issuesTable.horizontalHeader().setStretchLastSection(True)
        for idx in range(len(self.issuesList)):
            checkbox_item = QTableWidgetItem()
            checkbox_item.setText(self.issuesList[idx])
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            if idx in checked_issues:
                checkbox_item.setCheckState(Qt.Checked)
            else:
                checkbox_item.setCheckState(Qt.Unchecked)
            self.issuesTable.setItem(idx, 0, checkbox_item)
        self.issuesTableIsComplete = True

    def on_issuesTableChanged(self):
        if not self.issuesTableIsComplete:
            return
        self.checkedIssuesList.clear()
        for rowIndex in range(self.issuesTable.rowCount()):
            if self.issuesTable.item(rowIndex, 0).checkState() == Qt.Checked:
                self.checkedIssuesList.append(rowIndex)
        self.parent.projectSaved = False
        self.parent.saveProjectAction.setEnabled(True)
        self.parent.toolbarSave.setEnabled(True)

    def accept(self) -> None:
        currentVideoIndex = self.parent.videoList.currentVideoIndex
        self.parent.videoListWidget.setCurrentRow(currentVideoIndex)
        super().accept()

    def reject(self) -> None:
        currentVideoIndex = self.parent.videoList.currentVideoIndex
        self.parent.videoListWidget.setCurrentRow(currentVideoIndex)
        super().reject()

    def getQTableWidgetSize(self):
        w = self.issuesTable.verticalHeader().width() + 4  # +4 seems to be needed
        for i in range(self.issuesTable.columnCount()):
            w += self.issuesTable.columnWidth(i)  # seems to include gridline (on my machine)
        h = self.issuesTable.horizontalHeader().height() + 4
        for i in range(self.issuesTable.rowCount()):
            h += self.issuesTable.rowHeight(i)
        return QSize(w, h)

