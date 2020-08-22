import abc
import logging

import typing

from emoji_maniac.bot.config import Config
from emoji_maniac.log import get_logger
from emoji_maniac.persistence.models import EmojiSource, Emoji, MessageEmoji, StatsEmoji


class EmojiBackend(abc.ABC):
    log: logging.Logger
    config: Config

    def __init__(self, config: Config):
        self.config = config
        self.log = get_logger(type(self).__name__)

    @abc.abstractmethod
    async def submit_emoji(self, source: EmojiSource, emoji_obj: MessageEmoji):
        """
        Submits emoji to given source
        :param source: Source where emoji came from
        :param emoji_obj: Emoji representation
        """
        pass

    @abc.abstractmethod
    async def remove_emoji(self, source: EmojiSource, emoji_obj: Emoji):
        """
        Removes emoji for give source
        :param source: Source where emoji came from
        :param emoji_obj: Emoji representation
        """
        pass

    @abc.abstractmethod
    async def remove_emoji_source(self, source: EmojiSource):
        """
        Removes emoji source
        :param source: Source where emoji came from
        """
        pass

    @abc.abstractmethod
    async def get_emojis_top(self, guild_id: int = None, last_n_days: int = None,
                             user_id: int = None, limit: int = None) -> typing.List[StatsEmoji]:
        pass

    async def get_emojis_global_top10(self, guild_id: int):
        return await self.get_emojis_top(guild_id=guild_id, limit=10)


