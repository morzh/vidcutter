#!-*- coding:utf-8 -*-
import os
import sys

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QApplication, QListWidgetItem



class DemoListWidget(QDialog):
   def __init__(self):
      super().__init__()
      self.setupUi(self)

      self.listWidget.currentItemChanged.connect(self.cb_currentItemChanged)
      self.listWidget.currentRowChanged.connect(self.cb_currentRowChanged)
      self.listWidget.currentTextChanged.connect(self.cb_currentTextChanged)
      self.listWidget.itemActivated.connect(self.cb_itemActivated)
      self.listWidget.itemChanged.connect(self.cb_itemChanged)
      self.listWidget.itemClicked.connect(self.cb_itemClicked)

   def _init_data(self):
      _item = QListWidgetItem()
      _item.setData(Qt.DisplayRole, 'hello')
      _item.setData(Qt.UserRole, 'world')




def main():
   app = QApplication(sys.argv)
   dialog = DemoListWidget()
   dialog.show()
   app.exec_()


if __name__ == '__main__':
   main()