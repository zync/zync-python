
# Try importing from PySide (Maya 2016) first, then from PySide2 (Maya 2017)
# Alias the classes since some of them have been moved from PyGui to PyWidgets
try:
  import pysideuic
except:
  import pyside2uic as pysideuic

from cStringIO import StringIO

import xml.etree.ElementTree as ElementTree

def load_ui_type(filename):
  """Loads and parses ui file created by Qt Designer"""
  xml = ElementTree.parse(filename)
  # pylint: disable=no-member
  form_class = xml.find('class').text

  with open(filename, 'r') as ui_file:
    output_stream = StringIO()
    frame = {}

    pysideuic.compileUi(ui_file, output_stream, indent=0)
    compiled = compile(output_stream.getvalue(), '<string>', 'exec')
    # pylint: disable=exec-used
    exec compiled in frame

    form_class = frame['Ui_%s'%form_class]

  return form_class
