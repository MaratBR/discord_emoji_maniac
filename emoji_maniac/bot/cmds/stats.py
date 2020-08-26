import random
from datetime import datetime
from functools import partial

import typing

from emoji_maniac.bot import ds_utils
from emoji_maniac.bot.bot import CommandContext, Command
from emoji_maniac.persistence.models import StatsEmoji


class GetStatsCommand(Command):
    default_name = 'stats'
    TITLE = [
        '%s, here\'s the results',
        'Here you go %s',
        'This is what I found for you %s:',
        '%s'
    ]
    TITLE_GUILD_RESULTS = 'Guild stats – %s'
    TITLE_GUILD_RESULTS_PERIOD = 'Guild stats – _%s_ (%s)'

    TITLE_USERS_RESULTS = 'Personal stats of `%s`'
    TITLE_USERS_RESULTS_PERIOD = 'Personal stats of `%s` (%s)'

    async def execute(self, ctx: CommandContext):
        arg = ctx.get_arg(0) or ''
        arg = arg.lower()
        is_guild = False
        if 'guild'.startswith(arg) and arg != '':
            period = ctx.get_arg(1)
            is_guild = True
        else:
            period = arg
        if is_guild:
            await self._guild_stats(ctx, period)
        else:
            await self._user_stats(ctx, period)

    async def _guild_stats(self, ctx: CommandContext, period: str):
        await self._show_stats(ctx, ctx.message.guild.id, period=period)

    async def _user_stats(self, ctx: CommandContext, period: str):
        await self._show_stats(ctx, ctx.message.guild.id, ctx.message.author.id, period)

    @classmethod
    async def _show_stats(cls, ctx: CommandContext, guild_id: int, user_id: int = None, period: str = None):
        backend = ctx.parent.backend

        params = [ctx.message.author.display_name if user_id is not None else ctx.message.guild.name]
        has_period = True
        if period in ('year', 'y', 'annual'):
            coro = backend.get_emojis_top10_yearly(guild_id, user_id)
            params.append('this year')
        elif period in ('month', 'm'):
            coro = backend.get_emojis_top10_monthly(guild_id, user_id)
            params.append('this month')
        elif period in ('week', 'w'):
            coro = backend.get_emojis_top10_weekly(guild_id, user_id)
            params.append('this week')
        elif period in ('day', 'today', 'd'):
            coro = backend.get_emojis_top10_daily(guild_id, user_id)
            params.append('today')
        else:
            coro = backend.get_emojis_top10(guild_id, user_id)
            has_period = False

        if has_period:
            title = cls.TITLE_GUILD_RESULTS_PERIOD if user_id is None else cls.TITLE_USERS_RESULTS_PERIOD
        else:
            title = cls.TITLE_GUILD_RESULTS if user_id is None else cls.TITLE_USERS_RESULTS
        params = params[0] if len(params) == 1 else tuple(params)
        title = title % params
        subtitle = random.choice(cls.TITLE) % ctx.message.author.display_name

        await ds_utils.took_too_long_message_utility(
            ctx.message.channel,
            ttl_title='Loading...',
            ttl_msg=None,
            coro=coro,
            timeout=0,
            handler=partial(
                cls._stats_result_handler,
                ctx=ctx,
                title=title,
                subtitle=subtitle,
                user_id=user_id)
        )

    @staticmethod
    def _stats_result_handler(results: typing.List[StatsEmoji], dt: float, *,
                              ctx: CommandContext, title: str, subtitle: str, user_id: int):
        result = results
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
                msg += str(ctx.parent.bot.get_emoji(e.emoji.emoji_id))
            else:
                msg += e.emoji.unicode_char
            msg += f'\t— {e.total_mentions} mentions, {round(e.percentage)}%\n'

        embed = ds_utils.create_embed(
            title=title % params,
            description=msg,
            td=dt,
            thumbnail=None if user_id is None else ctx.message.author.avatar_url
        )
        return embed

