import asyncio
import random
import time
from functools import partial

import emoji
import typing

import emoji_maniac.bot.ds_utils as ds_utils

from emoji_maniac.bot.bot import Command, CommandContext
from emoji_maniac.persistence.models import StatsEmoji, EmojiSource, MessageEmoji
from emoji_maniac.persistence.utils import pack2b64


class PingCommand(Command):
    default_name = 'ping'

    async def execute(self, ctx: CommandContext):
        await ctx.message.channel.send(f'{ctx.message.author.mention} :ping_pong:')


class RandomEmojiCommand(Command):
    default_name = 'random'

    async def execute(self, ctx: CommandContext):
        type_ = ctx.get_arg(0)
        if type_ is not None:
            type_ = type_.lower()
        if type_ == 'custom':
            emojis = ctx.parent.client.emojis
        elif type_ == 'unicode':
            emojis = emoji.EMOJI_UNICODE.values()
        else:
            emojis = list(emoji.EMOJI_UNICODE.values()) + ctx.parent.client.emojis
        await ctx.message.channel.send(str(random.choice(emojis)))


class GetStatsCommand(Command):
    default_name = 'stats'
    TITLE = [
        '%(username)s, here\'s the results',
        'Here you go %(username)s',
        'This is what I found for you %(username)s:',
        '%(username)s'
    ]
    TITLE_GUILD_RESULTS = 'Guild stats'
    TITLE_GLOBAL_RESULTS = 'Global stats'
    TITLE_USERS_RESULTS = 'Personal stats of `%(user)s`'

    async def execute(self, ctx: CommandContext):
        arg = ctx.args.split(' ', 1)[0].strip().lower() if ctx.args else ''
        if arg == '':
            await self._user_stats(ctx)
        elif arg == 'guild':
            await self._guild_stats(ctx)
        elif arg == 'global':
            await self._global_stats(ctx)

    async def _guild_stats(self, ctx: CommandContext):
        await self._show_stats(ctx, self.TITLE_GUILD_RESULTS, guild_id=ctx.message.guild.id)

    async def _user_stats(self, ctx: CommandContext):
        await self._show_stats(ctx, random.choice(self.TITLE),
                               self.TITLE_USERS_RESULTS,
                               guild_id=ctx.message.guild.id,
                               user_id=ctx.message.author.id)

    async def _global_stats(self, ctx: CommandContext):
        await self._show_stats(ctx, self.TITLE_GLOBAL_RESULTS)

    @classmethod
    async def _show_stats(cls, ctx: CommandContext, title: str, subtitle: str = None, guild_id: int = None,
                          user_id: int = None, limit: int = 10):
        await ds_utils.took_too_long_message_utility(
            ctx.message.channel,
            ttl_title='Loading...',
            ttl_msg=None,
            coro=cls._get_stats_cached(ctx, guild_id, user_id, limit),
            timeout=0,
            handler=partial(cls._stats_result_handler, ctx=ctx, title=title, subtitle=subtitle, user_id=user_id)
        )

    @staticmethod
    def _stats_result_handler(results: typing.List[StatsEmoji], dt: float, *,
                              ctx: CommandContext, title: str, subtitle: str, user_id: int):
        result, from_cache = results
        params = {
            'username': ctx.message.author.display_name,
            'mention': ctx.message.author.mention,
            'user': str(ctx.message.author)
        }
        msg = ''
        if subtitle is not None:
            msg += subtitle % params + '\n'
        for e in result:
            if e.emoji.is_custom:
                msg += str(ctx.parent.client.get_emoji(e.emoji.emoji_id))
            else:
                msg += e.emoji.unicode
            msg += f'\t— {e.total_mentions} mentions, {round(e.percentage)}%\n'

        embed = ds_utils.create_embed(
            title=title % params,
            description=msg,
            td=dt,
            thumbnail=None if user_id is None else ctx.message.author.avatar_url,
            from_cache=from_cache
        )
        return embed

    @staticmethod
    async def _get_stats_cached(ctx: CommandContext, guild_id: int = None, user_id: int = None, limit: int = 10):
        cache_key = f'stats-t{limit}'
        if guild_id is None:
            cache_key += '-g'
        else:
            cache_key += f'-{pack2b64("<Q", guild_id)}'
        if user_id is not None:
            cache_key += f'-{pack2b64("<Q", user_id)}'
        result = await ctx.parent.backend.get_cache(cache_key)
        if result is None:
            result = await ctx.parent.backend.get_emojis_top(guild_id, user_id=user_id, limit=limit)
            await ctx.parent.backend.put_cache(cache_key, result)
            return result, False
        else:
            return result, True


class PopulateCommand(Command):
    async def execute(self, ctx: CommandContext):
        try:
            size = max(int(ctx.get_arg(0)), 100)
        except:
            size = 100

        source = EmojiSource.from_message(ctx.message)
        emojis = list(emoji.EMOJI_UNICODE.keys())
        records = [
            (source, MessageEmoji.unicode(random.choice(emojis)[1:-1]))
            for i in range(size)
        ]
        await ctx.parent.backend.submit_bulk(records)
        await ctx.message.channel.send(f'{ctx.message.author.mention} DONE {size} records created!')

    default_name = 'populate'
