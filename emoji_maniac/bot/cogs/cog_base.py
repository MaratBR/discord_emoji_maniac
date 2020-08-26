import logging

from discord.ext import commands
from emoji_maniac.log import get_logger
from emoji_maniac.persistence.emoji_backend import EmojiBackend, BackendCog


class CogBase(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._log = None

    @property
    def log(self) -> logging.Logger:
        if self._log is None:
            self._log = get_logger(type(self))
        return self._log

    @property
    def backend(self) -> EmojiBackend:
        backend_cog: BackendCog = self.bot.get_cog('BackendCog')
        return backend_cog.b
