"""Dialog to express consent to use PVM instances
"""

import os

# Try importing from PySide (Maya 2016) first, then from PySide2 (Maya 2017)
# Alias the classes since some of them have been moved from PyGui to PyWidgets
try:
  import pysideuic
  import PySide.QtGui
  import PySide.QtCore as QtCore

  QCheckBox = PySide.QtGui.QCheckBox
  QDialog = PySide.QtGui.QDialog
  QDir = QtCore.QDir
  QDialogButtonBox = PySide.QtGui.QDialogButtonBox
  QFileSystemModel = PySide.QtGui.QFileSystemModel
  QHeaderView = PySide.QtGui.QHeaderView
  QTreeView = PySide.QtGui.QTreeView
  QPushButton = PySide.QtGui.QPushButton

  pysideVersion = PySide.__version__
except:
  import pyside2uic as pysideuic
  import PySide2.QtCore as QtCore
  import PySide2.QtWidgets

  QCheckBox = PySide2.QtWidgets.QCheckBox
  QDialog = PySide2.QtWidgets.QDialog
  QDir = QtCore.QDir
  QFileSystemModel = PySide2.QtWidgets.QFileSystemModel
  QHeaderView = PySide2.QtWidgets.QHeaderView
  QTreeView = PySide2.QtWidgets.QTreeView
  QPushButton = PySide2.QtWidgets.QPushButton

  pysideVersion = PySide2.__version__

import dialog_helper
from settings import Settings

UI_PVM_CONSENT = '%s/resources/pvm_consent.ui' % os.path.dirname(__file__)

class PvmConsentDialog(QtCore.QObject):
  """Displays dialog allowing user to select files or directories"""
  def __init__(self, parent=None):
    """Constructs file selection dialog

    Params:
      project_name: str, name of Zync project
    """
    super(PvmConsentDialog, self).__init__(parent)
    self.settings = Settings.get()

    FormClass = dialog_helper.load_ui_type(UI_PVM_CONSENT)
    form_class = FormClass()
    self.dialog = QDialog()
    if parent:
      self.dialog.setParent(parent, QtCore.Qt.Window)
    form_class.setupUi(self.dialog)

    pushButton_yes = self.dialog.findChild(QPushButton, 'pushButton_yes')
    pushButton_yes.clicked.connect(self.accept)
    pushButton_no = self.dialog.findChild(QPushButton, 'pushButton_no')
    pushButton_no.clicked.connect(self.reject)

  def prompt(self):
    self.dialog.show()
    return self.dialog.exec_()

  def accept(self):
    checkBox_dontAsk = self.dialog.findChild(QCheckBox, 'checkBox_dontAsk')
    if checkBox_dontAsk.checkState():
      self.settings.put_pvm_ack(True)

    self.dialog.accept()
    self.dialog = None

  def reject(self):
    self.dialog.reject()
    self.dialog = None
