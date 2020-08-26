import abc
import logging

import typing
from datetime import timedelta

import discord

from emoji_maniac.bot.config import Config
from emoji_maniac.log import get_logger
from emoji_maniac.persistence.models import EmojiSource, Emoji, MessageEmoji, StatsEmoji


class EmojiBackend(abc.ABC):
    log: logging.Logger
    config: Config

    def __init__(self, config: Config):
        self.config = config
        self.log = get_logger(type(self).__name__)

    async def init(self):
        pass

    @abc.abstractmethod
    async def submit_reaction(self, guild_id: int, message_id: int, user_id: int, emoji: Emoji):
        pass

    @abc.abstractmethod
    async def remove_reaction(self, guild_id: int, message_id: int, user_id: int, emoji: Emoji):
        pass

    @abc.abstractmethod
    async def submit_message(self, message: discord.Message, emojis: typing.List[MessageEmoji]):
        pass

    @abc.abstractmethod
    async def get_emojis_top10(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        pass

    @abc.abstractmethod
    async def get_emojis_top10_yearly(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        pass

    @abc.abstractmethod
    async def get_emojis_top10_monthly(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        pass

    @abc.abstractmethod
    async def get_emojis_top10_weekly(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        pass

    @abc.abstractmethod
    async def get_emojis_top10_daily(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        pass

    @abc.abstractmethod
    async def get_cache(self, key: str):
        pass

    @abc.abstractmethod
    async def put_cache(self, key: str, value, age: timedelta = timedelta(minutes=10)):
        pass

    @abc.abstractmethod
    async def clear_cache(self):
        pass


