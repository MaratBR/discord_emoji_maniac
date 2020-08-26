import base64
from dataclasses import dataclass
from functools import cached_property

import discord
import emoji

from emoji_maniac.persistence.utils import pack2b64, pack2b64_bin, unpack_from_b64


@dataclass
class Emoji:
    is_custom: bool
    name: str
    emoji_id: int = None

    @cached_property
    def uid(self):
        if self.is_custom:
            return 'c' + pack2b64('<Q', self.emoji_id) + ':' + self.name
        else:
            emoji_unicode = emoji.EMOJI_UNICODE[f':{self.name}:']
            emoji_bytes = emoji_unicode.encode('utf-16be')
            return 'u' + base64.b64encode(emoji_bytes).decode('ascii') + ':' + self.name

    @property
    def unicode_char(self):
        return emoji.EMOJI_UNICODE.get(f':{self.name}:')

    @classmethod
    def from_uid(cls, uid: str):
        parts = uid[1:].split(':')
        if len(parts) != 2:
            return None
        type_ = uid[0]
        name = parts[1]
        if type_ == 'u':
            if f':{name}:' in emoji.EMOJI_UNICODE:
                return cls(name=name, is_custom=False)
            return None
        elif type_ == 'c':
            try:
                emoji_id = unpack_from_b64('<Q', parts[0])[0]
                return cls(is_custom=True, name=name, emoji_id=emoji_id)
            except:
                return None


@dataclass
class MessageEmoji(Emoji):
    count: int = 1

    @classmethod
    def custom(cls, name: str, emoji_id: int, count: int = 1) -> 'MessageEmoji':
        return cls(True, name, emoji_id, count)

    @classmethod
    def unicode(cls, name: str, count: int = 1) -> 'MessageEmoji':
        return cls(False, name, count=count)

    @classmethod
    def from_reaction(cls, reaction: discord.RawReactionActionEvent) -> 'MessageEmoji':
        msg_emoji: discord.PartialEmoji = reaction.emoji
        if msg_emoji.is_unicode_emoji():
            return cls.unicode(emoji.UNICODE_EMOJI[msg_emoji.name][1:-1])
        else:
            return cls.custom(msg_emoji.name, msg_emoji.id)


@dataclass
class StatsEmoji:
    emoji: Emoji
    total_mentions: int
    percentage: float


@dataclass
class EmojiSource:
    """

    EmojiSource represents the source where emoji came from, it can be either a message (content with emojis)
    or it can be a reaction

    """

    guild_id: int
    message_id: int
    user_id: int
    reaction: bool = False

    @cached_property
    def uid(self):
        return pack2b64('<?QQQ', self.reaction, self.guild_id, self.user_id, self.message_id)

    @classmethod
    def from_message(cls, message: discord.Message, reaction: bool = False):
        guild: discord.Guild = message.guild
        return cls(
            guild_id=guild.id,
            message_id=message.id,
            user_id=message.author.id,
            reaction=reaction
        )

    @classmethod
    def from_reaction(cls, reaction: discord.RawReactionActionEvent):
        return cls(
            reaction=True,
            guild_id=reaction.guild_id,
            message_id=reaction.message_id,
            user_id=reaction.user_id
        )
