#!/usr/bin/env python
# """Unittests for analytics.py"""
import unittest

import analytics


class TestAnalytics(unittest.TestCase):

  def test_format_error_should_shorten_stack_traces(self):
    error = """Traceback (most recent call last):
  File "/usr/local/zync/analytics.py", line 154, in main
    test_exception()
  File "/usr/local/zync/analytics.py", line 140, in test_exception
    raise Exception('test error2')
Exception: test error2
      """

    result = analytics.format_error(error)

    expected = """/u/l/z/analytics.py:154, in main
    test_exception()
  /u/l/z/analytics.py:140, in test_exception
    raise Exception('test error2')
Exception: test error2"""
    self.assertEqual(expected, result)

  def test_format_error_should_cut_least_important_part_of_stack_trace(self):
    error = """Traceback (most recent call last):
  File "/usr/local/zync/analytics.py", line 154, in main
    test_exception()
  File "/usr/local/zync/analytics.py", line 140, in test_exception
    raise Exception('test error2')
Exception: test error2
      """

    result = analytics.format_error(error, limit=100)

    expected = """/u/l/z/analytics.py:140, in test_exception
    raise Exception('test error2')
Exception: test error2"""
    self.assertEqual(expected, result)

  def test_format_error_should_shorten_paths_with_spaces(self):
    error = """File "c:\\Programs and Files\\Secret App\\app.py", line 140, in test_exception
    raise Exception('test error2')
Exception: Invalid "c:\\Programs and Files\\Secret App\\secret texture.tx"
      """

    result = analytics.format_error(error)

    expected = '''c:/P/S/app.py:140, in test_exception
    raise Exception('test error2')
Exception: Invalid "c:/P/S/s.tx"'''
    self.assertEqual(expected, result)

  def test_format_error_should_truncate_error(self):
    error = "A long error message"

    result = analytics.format_error(error, limit=12)

    expected = "A long error"
    self.assertEqual(expected, result)

  def test_format_error_should_mask_filename(self):
    error = "File /home/file.txt does not exist."

    result = analytics.format_error(error)

    expected = "File /h/f.txt does not exist."
    self.assertEqual(expected, result)

  def test_format_error_should_shorten_linux_absolute_paths(self):
    error = "File /home/secret_user_name/file.txt does not exist."

    result = analytics.format_error(error)

    expected = "File /h/s/f.txt does not exist."
    self.assertEqual(expected, result)

  def test_format_error_should_shorten_windows_absolute_paths(self):
    error = "File c:\\users\\secret_user_name\\file.txt does not exist."

    result = analytics.format_error(error)

    expected = "File c:/u/s/f.txt does not exist."
    self.assertEqual(expected, result)

  def test_format_error_should_shorten_path_with_spaces(self):
    error = "File c:\\Program Files\\secret_user_name\\file.txt does not exist."

    result = analytics.format_error(error)

    expected = "File c:/P F/s/f.txt does not exist."
    self.assertEqual(expected, result)

  def test_format_error_should_shorten_two_part_linux_absolute_paths(self):
    error = "File /home/file.txt does not exist."

    result = analytics.format_error(error)

    expected = "File /h/f.txt does not exist."
    self.assertEqual(expected, result)

  def test_format_error_should_shorten_short_windows_absolute_paths(self):
    error = "File c:\\users\\file.txt does not exist."

    result = analytics.format_error(error)

    expected = "File c:/u/f.txt does not exist."
    self.assertEqual(expected, result)

  def test_format_error_should_shorten_linux_relative_paths(self):
    error = "File home/secret_user_name/file.txt does not exist."

    result = analytics.format_error(error)

    expected = "File h/s/f.txt does not exist."
    self.assertEqual(expected, result)

  def test_format_error_should_shorten_windows_relative_paths(self):
    error = "File users\\secret_user_name\\file.txt does not exist."

    result = analytics.format_error(error)

    expected = "File u/s/f.txt does not exist."
    self.assertEqual(expected, result)

  def test_format_error_should_not_shorten_single_slashes(self):
    error = "App maya\\2018 c4d/21"

    result = analytics.format_error(error)

    self.assertEqual(error, result)

  def test_format_error_should_mask_emails(self):
    error = "User secret@gmail.com does not exist."

    result = analytics.format_error(error)

    expected = "User <email> does not exist."
    self.assertEqual(expected, result)


def main():
  unittest.main()


if __name__ == '__main__':
  main()
