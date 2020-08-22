import typing
import logging
from dataclasses import dataclass

from emoji_maniac.log import get_logger

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


@dataclass
class CacheConfig:
    enabled: bool = True


class Config:
    token: str = None
    _filename: str
    _data: dict
    log: logging.Logger
    cache_cfg: CacheConfig = CacheConfig()

    def __init__(self, filename: str):
        self._filename = filename
        self.log = get_logger(self.__class__)
        self.refresh()

    def refresh(self):
        d = self._get_data()
        if d is None:
            print('Failed to refresh config')
            return
        self.token = d.get('token')
        self._data = d

        try:
            self.cache_cfg = CacheConfig(**d['cache'])
        except:
            pass

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

