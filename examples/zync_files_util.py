#!/usr/bin/env python
"""A script for listing files previously uploaded to Zync.

Example usage:
  ./zync_files_util.py project_name list /
"""
import argparse
import os
import sys
import urllib

#   Go two levels up and add that directory to the PATH, so we can find zync.py.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import zync


DEFAULT_MAX_DIR_DEPTH = 20


def _format_file_size(size):
  """Formats size in human readable form.

  Args:
    size: int, Size in bytes.
  Returns:
    str, Human readable size.
  """
  kilo = 1024.0
  for unit in ['B', 'KB', 'MB', 'GB']:
    if size < kilo:
      suffix = unit
      break
    size /= kilo
  else:
    suffix = 'TB'
  return "%.1f %s" % (size, suffix)


def _build_gcs_prefix(project, path):
  """For given project name and file path prefix returns GCS prefix.
  
  Args:
    project: str, Project name. 
    path: str, File path prefix. e.g. 'C:/my/assets'
  Returns:
    str, GCS path prefix.
  """
  maybe_slash = '' if path[0] == '/' else '/'
  return 'projects/' + project + maybe_slash + path


def _get_files(project, prefix, max_depth=DEFAULT_MAX_DIR_DEPTH):
  """Fetches data from Zync API.
  
  Args:
    project: str, Project name.
    prefix: str, File path prefix.
    max_depth: int, Max directory recursion.
  Returns:
    [dict], A structure describing files structure. See zync.Zync().list_files.
  """
  return zync.Zync().list_files(
      _build_gcs_prefix(project, prefix), recursive=True, max_depth=max_depth)


def _recursively_print_files(node, is_last=True, indent=''):
  """Prints a files tree.
  
  Example output:
  +--nuke
   +--10.0
   |  +--data1
   |  |  +--foo.png
   |  |  +--bar.png
   |  +--data2
   |     +--baz.ext
   +--11.0
      +--data1
      |  +--output.0000.exr
      +--data1
         +--out.0001.exr
         +--out.0010.exr

  Args:
    node: dict, A structure describing a file.
    is_last: Tells if the file is a last one on the list.
    indent: str, A prefix for printed lines.
  """
  print indent + '+--' + node['name']
  new_indent = indent + ('   ' if is_last else '|  ')
  children = node.get('children', [])
  for index, child in enumerate(children):
    child_is_last = index == len(children) - 1
    _recursively_print_files(child, child_is_last, new_indent)


def list_files(project, prefix, max_depth=DEFAULT_MAX_DIR_DEPTH):
  """Lists files stored in a Zync project.
  
  Args:
    project: str, Name of a project. 
    prefix: str, Files path prefix.
    max_depth: int, Maximum depth of the recursion.
  """
  for node in _get_files(project, prefix, max_depth):
    _recursively_print_files(node)


def _confirm_default_yes(prompt, skip=False):
  """Prompts user to confirm action.

  Args:
    prompt: str, Prompt text.
    skip: bool, If True the function returns True without prompting.
  """
  if skip:
    print prompt
    return True
  else:
    print prompt + ' Please confirm [Y/n]'

  yes = ['yes', 'y', '']
  no = ['no', 'n']

  while True:
    choice = raw_input().lower()
    if choice in yes:
       return True
    elif choice in no:
       return False


def _total_number_and_size_of_files(files_tree):
  """Calculates a total size and number of files in the file tree.
  
  A node describing a file/directory contains:
    url: str, If present we consider a file to be downloadable and 
              expect 'size_bytes'.
    size_bytes: int, Size of the file in bytes
    children: [dict], List of children of the directory.
  
  Args:
    files_tree: dict(), A structure describing files.
    
  Returns: (int, int), Number of files and total size of the files in bytes.
  """
  total_files = 0
  total_size = 0
  if 'url' in files_tree:
    total_files += 1
    total_size += files_tree.get('size_bytes', 0)
  for child in files_tree.get('children', []):
    child_files, child_size = _total_number_and_size_of_files(child)
    total_files += child_files
    total_size += child_size
  return total_files, total_size


def _download_file(url, dest_path, filename, skip_confirm, size):
  """Creates intermediate directories and downloads a file.

  Args:
    url: str, The remote location of the file.
    dest_path: str, Path to the destination directory.
    filename: str, Name of the file.
    skip_confirm: boolean, If true, don't ask for the confirmation.
    size: str, Size of the file.
  """

  def _reporthook(count, block_size, total_size):
    percent = int(count * block_size * 100 / total_size)
    sys.stdout.write("\r...%3d%%, %s" % (
      percent, _format_file_size(count * block_size).rjust(20)))
    sys.stdout.flush()

  file_path = os.path.join(dest_path, filename)
  confirm_text = 'File %s (%s)' % (file_path, size)
  if not _confirm_default_yes(confirm_text, skip_confirm):
    return

  _maybe_makedirs(dest_path)

  override_confirmation = 'The file exists. Override?'
  if (not os.path.exists(file_path) or
      _confirm_default_yes(override_confirmation, skip_confirm)):
    urllib.urlretrieve(url, file_path, _reporthook)
    # print a newline after the _reporthook text
    print


def _maybe_makedirs(dest_path):
  """Creates a directory if necessary.
  
  Args:
    dest_path: str, Absolute path to a directory
  """
  if not os.path.exists(dest_path):
    os.makedirs(dest_path)


def download_files(project, prefix, dest='.', max_depth=10, skip_confirm=False):
  """Downloads files form Zync.
  
  Args:
    project: str, Name of a project. 
    prefix: str, Files path prefix.
    dest: str, Path where the files should be saved.
    max_depth: int, Maximum depth of the recursion.
    skip_confirm: bool, If True, performs actions without confirmation.
  """
  files_tree = dict(
    children=_get_files(project, prefix, max_depth),
    name='')
  num_of_files, total_size = _total_number_and_size_of_files(files_tree)
  global_confirm = ("%s files (%s) is going to be downloaded to '%s'. " %
                    (num_of_files, _format_file_size(total_size), dest))
  if not _confirm_default_yes(global_confirm, skip_confirm):
    return

  def maybe_download(node, current_path):
    if 'url' in node and node['url'] != '#':
      _download_file(node['url'], current_path, node['name'],
                     skip_confirm, node.get('fsize', 'unknown size'))
    for child in node.get('children', []):
      child_path = os.path.join(current_path, node['name'])
      maybe_download(child, child_path)

  maybe_download(files_tree, os.path.abspath(dest))
  print 'Done'


def main():
  parser = argparse.ArgumentParser(description=__doc__)

  parser.add_argument('project', help='Project name')

  subparsers = parser.add_subparsers(metavar='ACTION', dest='action')

  parent_parser = argparse.ArgumentParser(add_help=False)
  parent_parser.add_argument('prefix',
                             help='A path of the directory to be listed')
  parent_parser.add_argument('--max-depth', default=DEFAULT_MAX_DIR_DEPTH)

  # Listing files
  parser_list = subparsers.add_parser(
      'list', help='List files', parents=[parent_parser])
  # Downloading files
  parser_download = subparsers.add_parser(
      'download', help='Download files', parents=[parent_parser])
  parser_download.add_argument('--dest', default='.')
  parser_download.add_argument(
       '--yes', action='store_true', help='Skip confirmation')

  args = parser.parse_args()

  if args.action == 'list':
    list_files(args.project, args.prefix, args.max_depth)
  if args.action == 'download':
    download_files(
        args.project, args.prefix, args.dest, args.max_depth, args.yes)


if __name__ == "__main__":
  main()
