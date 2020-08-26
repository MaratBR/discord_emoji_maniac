import abc
import asyncio
import inspect
import re
from datetime import datetime
from functools import cached_property

import discord
import typing

from .emoji import (get_emojis, MessageEmoji)
from emoji_maniac.log import get_logger
from logging import Logger
from .config import Config
from ..persistence.emoji_backend import EmojiBackend, EmojiSource


class BotContext:
    _bot: 'Bot'

    @property
    def config(self):
        return self._bot.config

    @property
    def client(self):
        return self._bot.client

    @property
    def backend(self) -> 'EmojiBackend':
        return self._bot.backend

    def __init__(self, bot: 'Bot'):
        self._bot = bot


class CommandContext:
    parent: BotContext
    args: str
    message: discord.Message

    @property
    def args_or_empty(self):
        return self.args or ''

    @cached_property
    def args_array(self):
        if self.args is None:
            return []
        return re.split(r"\s+", self.args.strip())

    def get_arg(self, index: int):
        args = self.args_array
        if len(args) <= index:
            return None
        return args[index]

    def __init__(self, bot_ctx: BotContext, args: str, message: discord.Message):
        self.parent = bot_ctx
        self.args = args
        self.message = message

    @property
    def sender(self) -> discord.User:
        return self.message.author


class Command(abc.ABC):
    @abc.abstractmethod
    async def execute(self, ctx: CommandContext):
        pass

    default_name: str = None


class FuncCommand(Command):
    async def execute(self, ctx: CommandContext):
        if inspect.iscoroutinefunction(self._func):
            await self._func(ctx)
        else:
            self._func(ctx)

    def __init__(self, func):
        self._func = func


class FFCCommand(Command, abc.ABC):
    def matches(self, text: str) -> bool:
        pass


class Module(abc.ABC):
    bot: 'Bot'
    activated: bool = False

    def __init__(self, bot: 'Bot'):
        self.bot = bot

    def activate(self):
        if self.activated:
            return
        self.activated = True
        self._activate()

    @abc.abstractmethod
    def _activate(self):
        pass

    def deactivate(self):
        if not self.activated:
            return
        self.activated = False
        self._deactivate()

    @abc.abstractmethod
    def _deactivate(self):
        pass

    @abc.abstractmethod
    def get_description(self) -> str:
        pass

    @abc.abstractmethod
    def get_display_name(self) -> str:
        pass


class ModuleBase(Module, abc.ABC):
    _commands: list

    def __init__(self, bot: 'Bot'):
        super(ModuleBase, self).__init__(bot)
        self._commands = []

    def register_command(self, command: typing.Union[Command, typing.Type[Command]], name: str = None):
        self._commands.append((command, name))

    def _activate(self):
        for (c, n) in self._commands:
            self.bot.register_command(c, n)

    def _deactivate(self):
        for (c, _) in self._commands:
            self.bot.unregister_command(c)


class Bot:
    client: discord.Client
    config: Config
    log: Logger
    _commands: typing.Dict[str, Command]
    _modules: typing.Dict[str, Module]
    _ctx: BotContext

    def __init__(self, backend: typing.Type[EmojiBackend], cfg_file='emoji_cfg.yaml', client_args: dict = None):
        self.log = get_logger()
        self.log.info('Initializing bot...')
        self.config = Config(cfg_file)
        self.client = self._create_client(client_args)
        self.backend = backend(self.config)
        self._ctx = BotContext(self)
        self._commands = {}
        self._modules = {}

    def run(self):
        """
        Runs the bot. Blocking call
        """
        self.client.run(self.config.token)

    def register_command(self, command: typing.Union[Command, typing.Type[Command], typing.Callable], name: str = None):
        """
        Registers the command
        :param command: Command instance or a subclass of Command or a function
        :param name: Name of command, overrides default_name of command
        """
        name = name or command.default_name
        if name is None:
            raise ValueError(f'Command {command.__class__.__name__} does not have a default name, please specify name '
                             f'explicitly')
        if self._commands.get(name) is not None:
            raise ValueError('Command {name} already registered')
        if inspect.isclass(command):
            if not issubclass(command, Command):
                raise TypeError('Command must inherit class Command or be a function')
            else:
                command = command()
        elif inspect.isfunction(command):
            command = FuncCommand(command)
        self._commands[name] = command

    def unregister_command(self, name: typing.Union[str, Command, typing.Type[Command]]):
        """
        Removes the command
        :param name:
            name of the command, must not be None,
            can be either a string or a command instance or command subclass
        """
        name = name if isinstance(name, str) else name.default_name
        if name is None:
            raise ValueError('name argument must be set')
        if name in self._commands:
            del self._commands[name]
        else:
            self.log.warning(f'failed to remove command {name} - command not found')

    def command(self, name: str = None):
        """
        Returns a decorator for registering commands.
        Decorator passes whatever is decorated with to register_command method.

        :param name: name of the command, optional
        :return: decorate function
        """
        def decorator(func):
            self.register_command(func, name)
            return func
        return decorator

    def add_module(self, module_class: typing.Type[Module]):
        module = module_class(self)
        self._modules[module_class.__name__] = module

    def activate_module(self, module_class: typing.Type[Module]):
        module = self._modules.get(module_class.__name__)
        if module is not None:
            module.activate()
        else:
            self.log.debug('Trying to activate module that does not exist')

    def _create_client(self, args: dict) -> discord.Client:
        args = args or {}
        c = discord.Client(**args)
        c.event(self.on_ready)
        return c

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._submit_emojis_on_reaction(payload, False)

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._submit_emojis_on_reaction(payload, True)

    async def on_ready(self):
        self.log.info(f'Modules list is locked, modules cannot be added anymore. Modules list: ' +
                      ', '.join(map(lambda m: type(m).__name__, self._modules.values())))
        for m in self._modules.values():
            m.activate()

        self.log.info(f'Bot is ready - {self.client.user.name}')
        self.log.info(f'Initializing {type(self.backend).__name__} backend...')
        await self.backend.init()
        self.log.info(f'Initializing {type(self.backend).__name__} backend COMPLETE')

        c = self.client
        c.event(self.on_message)
        c.event(self.on_raw_reaction_add)
        c.event(self.on_raw_reaction_remove)
        c.event(self.on_guild_join)
        c.event(self.on_guild_remove)

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

    async def on_message(self, message: discord.Message):
        if message.author == self.client.user:
            return

        for prefix in [f"<@{self.client.user.id}>", f"<@!{self.client.user.id}>"]:
            if message.content.startswith(prefix):
                # this message contains command, so we'll ignore processing
                # and just handle the command
                stripped = message.content[len(prefix):].strip()
                parts = stripped.split(' ', 1)
                command = self._commands.get(parts[0])
                if command is not None:
                    args = parts[1] if len(parts) == 2 else None
                    self.log.debug(f'Command issued: {parts[0]}, arguments: {args}')
                    ctx = CommandContext(self._ctx, args, message)
                    await command.execute(ctx)
                    return
                else:
                    # If there is no corresponding command, let's try to find if anything matches in FFC

                    self.log.debug(f'Unknown command issued: {parts[0]}, ignoring')

        await self._handle_incoming_message(message)

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
