import abc
import asyncio
import inspect
import re
from datetime import datetime
from functools import cached_property

import discord
import typing

from discord.ext import commands

from .cogs.default import EmojiCog
from .emoji import (get_emojis, MessageEmoji)
from emoji_maniac.log import get_logger
from logging import Logger
from .config import Config
from ..persistence.emoji_backend import EmojiBackend, EmojiSource, BackendCog


class BotContext(commands.Cog):
    _bot: 'Bot'

    @property
    def config(self):
        return self._bot.config

    @property
    def bot(self) -> discord.Client:
        return self._bot

    @property
    def backend(self) -> 'EmojiBackend':
        return self._bot.backend

    def __init__(self, bot: 'Bot'):
        self._bot = bot


class CommandContext:
    parent: BotContext
    cmd_ctx: commands.Context

    def __init__(self, bot_ctx: BotContext, cmd_context: commands.Context):
        self.parent = bot_ctx
        self.cmd_ctx = cmd_context

    @property
    def sender(self) -> discord.User:
        return self.cmd_ctx.author

    @property
    def backend(self) -> EmojiBackend:
        return self.parent.backend

    @property
    def config(self):
        return self.parent.config

    @property
    def message(self):
        return self.cmd_ctx.message


class Bot(commands.Bot):
    class CommandHandlerType(typing.Protocol):
        def __call__(self, context: CommandContext, *args: typing.Any):
            pass

    COMMAND_HANDLER_TYPE = CommandHandlerType
    DEFAULT_PREFIX = '::'

    config: Config
    backend: EmojiBackend
    log: Logger
    _ctx: BotContext
    _cmd_bot: commands.Bot

    def __init__(self, backend: typing.Type[EmojiBackend], cfg_file='emoji_cfg.yaml', **kwargs):
        super(Bot, self).__init__(command_prefix=self._determine_prefix, **kwargs)
        self.log = get_logger()
        self.log.info('Initializing bot...')
        self.config = Config(cfg_file)
        self.backend = backend(self.config)
        self._ctx = BotContext(self)

        self._init_cogs()

    def _init_cogs(self):
        self.add_cog(self._ctx)
        self.add_cog(self.config)
        self.add_cog(BackendCog(self.backend))
        self.add_cog(EmojiCog(self))

    def run(self):
        """
        Runs the bot. Blocking call
        """
        super(Bot, self).run(self.config.token)

    def _create_client(self, args: dict):
        args = args or {}
        c = commands.Bot(command_prefix=self._determine_prefix, **args)
        c.add_listener(self.on_ready)
        return c

    async def _determine_prefix(self, _, message: discord.Message):
        for prefix in [f"<@{self.user.id}> ", f"<@!{self.user.id}> "]:
            if message.content.strip().startswith(prefix):
                return prefix
        return (await self.backend.get_guild_prefix(message.guild.id)) or self.DEFAULT_PREFIX

    async def on_ready(self):
        self.log.info(f'Bot is ready - {self.user.name}')
        self.log.info(f'Initializing {type(self.backend).__name__} backend...')
        await self.backend.init()
        self.log.info(f'Initializing {type(self.backend).__name__} backend COMPLETE')

    async def on_guild_join(self, guild: discord.Guild):
        self.log.info(f'Bot joined guild "{guild.name}" ({guild.id})')
        if not await self.backend.has_guild_config(guild.id):
            await self.backend.update_guild_config(guild.id, {
                'joined_at': datetime.utcnow(),
                'tz_offset': 0,
                'lang': 'en',
                'active': True
            })
        else:
            await self.backend.update_guild_config(guild.id, {
                'active': True
            })

    async def on_guild_remove(self, guild: discord.Guild):
        if await self.backend.has_guild_config(guild.id):
            self.log.info(f'Bot left guild "{guild.name}" ({guild.id})')
            await self.backend.update_guild_config(guild.id, {
                'active': False,
                'last_deactivated_at': datetime.utcnow()
            })

