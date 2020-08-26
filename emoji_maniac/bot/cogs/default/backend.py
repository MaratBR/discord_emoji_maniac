import logging

import discord
from discord.ext import commands

from emoji_maniac.bot.cogs.cog_base import CogBase
from emoji_maniac.bot.emoji import get_emojis
from emoji_maniac.persistence.emoji_backend import EmojiBackend, BackendCog
from emoji_maniac.persistence.models import MessageEmoji


class LogBackendMixin:
    bot: commands.Bot
    log: logging.Logger
    backend: EmojiBackend

    @CogBase.listener('on_message')
    async def _on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        await self._handle_incoming_message(message)

    @CogBase.listener('on_raw_reaction_add')
    async def _on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._submit_emojis_on_reaction(payload, False)

    @CogBase.listener('on_raw_reaction_remove')
    async def _on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._submit_emojis_on_reaction(payload, True)

    async def _handle_incoming_message(self, message: discord.Message, from_history: bool = False):
        await self._submit_emojis_on_message(message)
        self.log.info(f'New message from {message.author.display_name}: {message.content}')

    async def _submit_emojis_on_message(self, message: discord.Message):
        emojis = get_emojis(message.content)
        if len(emojis) == 0:
            return
        await self.backend.submit_message(message, emojis)

    async def _submit_emojis_on_reaction(self, reaction: discord.RawReactionActionEvent, removed: bool):
        emoji_obj = MessageEmoji.from_reaction(reaction)
        if removed:
            await self.backend.remove_reaction(reaction.guild_id, reaction.message_id, reaction.user_id, emoji_obj)
        else:
            await self.backend.submit_reaction(reaction.guild_id, reaction.message_id, reaction.user_id, emoji_obj)