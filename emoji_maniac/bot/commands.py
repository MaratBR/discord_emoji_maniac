import asyncio
import random
import time
from datetime import datetime

import discord
import emoji

from emoji_maniac.bot.bot import Command, CommandContext
from emoji_maniac.persistence.models import EmojiSource, MessageEmoji
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
        await self._show_stats(ctx, self.TITLE_GUILD_RESULTS)

    async def _user_stats(self, ctx: CommandContext):
        await self._show_stats(ctx, random.choice(self.TITLE), self.TITLE_USERS_RESULTS, user_id=ctx.message.author.id)

    async def _global_stats(self, ctx: CommandContext):
        await self._show_stats(ctx, self.TITLE_GLOBAL_RESULTS, global_stats=True)

    @classmethod
    async def _show_stats(cls, ctx: CommandContext, title: str, subtitle: str = None, global_stats: bool = False,
                          user_id: int = None, limit: int = 10):
        td = time.time()
        result = await cls._get_stats_cached(ctx, global_stats, user_id, limit)

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

        td = round((time.time() - td) * 1000)
        embed = discord.Embed(title=title % params, description=msg, color=discord.Colour(0xffff00),
                              timestamp=datetime.utcnow())
        embed.set_footer(text=f'{td}ms')
        await ctx.message.channel.send(ctx.message.author.mention, embed=embed)

    @staticmethod
    async def _get_stats_cached(ctx: CommandContext, global_stats: bool = False, user_id: int = None, limit: int = 10):
        cache_key = f'stats-t{limit}'
        if global_stats:
            cache_key += '-g'
        else:
            cache_key += f'-{pack2b64("<Q", ctx.message.guild.id)}'
        if user_id is not None:
            cache_key += f'-{pack2b64("<Q", user_id)}'
        result = await ctx.parent.backend.get_cache(cache_key)
        if result is None:
            result = await ctx.parent.backend.get_emojis_top(ctx.message.guild.id, user_id=user_id, limit=limit)
            await ctx.parent.backend.put_cache(cache_key, result)
            return result
        else:
            return result
