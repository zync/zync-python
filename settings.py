"""
Takes care of peristent config and job settings.
"""

import json
import os

import zync_lib.appdirs.appdirs as appdirs

class Settings(object):
  APP_NAME = 'Zync'
  APP_AUTHOR = 'Google'
  settings = None

  def __init__(self):
    self._config, self._aux_files = Settings._read()

  @staticmethod
  def get():
    if not Settings.settings:
      Settings.settings = Settings()
    return Settings.settings

  def get_aux_files(self, project_name):
    if project_name in self._aux_files:
      return self._aux_files[project_name]
    else:
      return []

  def put_aux_files(self, project_name, aux_files):
    self._aux_files[project_name] = aux_files
    self._write_aux_files()

  def get_pvm_ack(self):
    return self._config.get('pvm_ack', False)

  def put_pvm_ack(self, ack):
    self._config['pvm_ack'] = ack
    self._write_config()

  @staticmethod
  def _read():
    config_dir = Settings._alloc_config_dir()
    config_filename = os.path.join(config_dir, "config.json")
    if os.path.exists(config_filename):
      with open(config_filename, "r") as config_file:
        config = json.load(config_file)
    else:
      config = {}
    aux_files_filename = os.path.join(config_dir, "aux_files.json")
    if os.path.exists(aux_files_filename):
      with open(aux_files_filename, "r") as aux_files_file:
        aux_files = json.load(aux_files_file)
    else:
      aux_files = {}

    return config, aux_files

  def _write_config(self):
    config_dir = Settings._alloc_config_dir()
    with open(os.path.join(config_dir, "config.json"), "w") as config_file:
      json.dump(self._config, config_file)

  def _write_aux_files(self):
    config_dir = Settings._alloc_config_dir()
    with open(os.path.join(config_dir, "aux_files.json"), "w") as aux_files_file:
      json.dump(self._aux_files, aux_files_file)

  @staticmethod
  def _alloc_config_dir():
    config_dir = appdirs.user_data_dir(appname=Settings.APP_NAME, appauthor=Settings.APP_AUTHOR)
    if not os.path.exists(config_dir):
      os.makedirs(config_dir)
    return config_dir
