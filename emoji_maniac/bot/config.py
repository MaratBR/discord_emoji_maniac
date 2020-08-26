import glob
import os
import random
import typing
import logging
from dataclasses import dataclass
from os import path

from emoji_maniac.log import get_logger
from discord.ext import commands

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


@dataclass
class CacheConfig:
    enabled: bool = True


DEFAULT_STORAGE_DIR = 'storage'


class I18NConfig:
    LANG_FILE_EXT = '.lang.yaml'

    def __init__(self, config: 'Config'):
        self.config = config
        self.fallback_language = 'en'
        self.log = get_logger(I18NConfig)
        self.translations = {}

    def get_available_translations(self):
        return list(self.translations.keys())

    def get(self, lang: str, key: str, params=None):
        value = self._get(lang, key)
        if value is None:
            return None
        elif isinstance(value, list):
            value = random.choice(value)
        if params is None:
            return value
        else:
            return value % params

    def get_list(self, lang: str, key: str) -> typing.Optional[typing.List[str]]:
        value = self._get(lang, key)
        if isinstance(value, list):
            return value
        return None

    def _get(self, lang: str, key: str):
        return self.translations.get(lang, {}).get(key) or self.translations.get(self.fallback_language, {}).get(key)

    def refresh_translations(self):
        directory = self.config.get_storage_dir('i18n')
        if path.isdir(directory):
            files = os.listdir(directory)
            files = list(filter(lambda f: path.isfile(path.join(directory, f)) and not f.startswith('_') and f.endswith(self.LANG_FILE_EXT), files))
        else:
            files = []
        self.log.info('Refreshing list of translations')
        translations = {}

        for file in files:
            language = file[:-len(self.LANG_FILE_EXT)]
            fullpath = path.join(directory, file)
            data = Loader(open(fullpath, encoding='utf-8')).get_data()
            if not isinstance(data, dict):
                self.log.warning(f'Invalid log file {file} contains valid yaml but '
                                 f'instead of dictionary contains: {type(data)}, file ignored')
                continue
            translation = {}
            for (k, v) in data.items():
                if isinstance(v, str) or isinstance(v, list) and all(isinstance(i, str) for i in v):
                    translation[k] = v
                else:
                    self.log.warning('Translation key "{k}" from file "{file}" is neither a string or a list of '
                                     'strings, key ignored')
            translations[language] = translation
        self.translations = translations


class Config(commands.Cog):
    token: str = None
    storage_dir: str = DEFAULT_STORAGE_DIR
    _filename: str
    _data: dict
    log: logging.Logger
    cache_cfg: CacheConfig = CacheConfig()
    _i18n: I18NConfig

    def __init__(self, filename: str):
        self._filename = filename
        self._i18n = I18NConfig(self)
        self.log = get_logger(self.__class__)
        self.refresh()

    def refresh(self):
        d = self._get_data()
        if d is None:
            print('Failed to refresh storage')
            return
        self.token = d.get('token')
        self.storage_dir = d.get('storage') or DEFAULT_STORAGE_DIR
        self._data = d

        try:
            self.cache_cfg = CacheConfig(**d['cache'])
        except:
            pass

        self._i18n.refresh_translations()

    @property
    def i18n(self):
        return self._i18n

    def get_backend_config(self, name: str):
        if self._data is None:
            return None
        cfg = self._data.get('emoji_backends', {}).get(name, {})
        if not isinstance(cfg, dict):
            return None
        return cfg

    T = typing.TypeVar('T')

    def require_backend_config_as(self, name: str, cls: T) -> T:
        return cls(**self.require_backend_config(name))

    def require_backend_config(self, name):
        cfg = self.get_backend_config(name)
        if cfg is None:
            raise TypeError(f'Configuration key "emoji_backends.{name}" must a dictionary')
        return cfg

    def get_storage_dir(self, name: str):
        return path.join(os.getcwd(), self.storage_dir, name)

    def _open_file(self, rw: bool=False) -> typing.IO:
        return open(self._filename, 'w+' if rw else 'r')
    
    def _get_data(self) -> dict or type(None):
        try:
            f = self._open_file()
            loader = Loader(f)
            data = loader.get_data()
            print(data)
            if not isinstance(data, dict):
                return None

            return data
        except Exception as exc:
            print(str(exc))

