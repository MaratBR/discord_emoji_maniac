from discord.ext import commands

from emoji_maniac.persistence.emoji_backend import BackendCog, EmojiBackend
from .backend import LogBackendMixin
from .commands import EmojiCommandsMixin
from ..cog_base import CogBase


class EmojiCog(LogBackendMixin, EmojiCommandsMixin, CogBase):
    pass
