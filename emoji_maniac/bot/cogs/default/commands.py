import time
import typing
from datetime import datetime

import discord
from discord.ext import commands

from emoji_maniac.bot import ds_utils
from emoji_maniac.bot.config import Config
from emoji_maniac.persistence.emoji_backend import EmojiBackend


class EmojiCommandsMixin:
    YEARLY = 1
    MONTHLY = 2
    WEEKLY = 3
    DAILY = 4
    TOTAL = 5
    PERIOD_DESCRIPTION = {
        YEARLY: 'this year',
        MONTHLY: 'this month',
        WEEKLY: 'this week',
        DAILY: 'today',
        TOTAL: 'total'
    }

    backend: EmojiBackend
    bot: commands.Bot

    @property
    def __cfg(self) -> Config:
        return self.bot.get_cog('Config')

    #region stats command

    class PeriodConverter(commands.Converter, int):

        async def convert(self, ctx, argument):
            argument = argument.lower().strip()
            if argument in ('y', 'year', 'yearly', 'annual'):
                return EmojiCommandsMixin.YEARLY
            elif argument in ('m', 'month', 'monthly'):
                return EmojiCommandsMixin.MONTHLY
            elif argument in ('w', 'week', 'weekly'):
                return EmojiCommandsMixin.WEEKLY
            elif argument in ('d', 't', 'today', 'day'):
                return EmojiCommandsMixin.DAILY
            else:
                return EmojiCommandsMixin.TOTAL

    @commands.command('stats')
    async def _send_user_stats(self, ctx: commands.Context, period: PeriodConverter = TOTAL, member: discord.User = None):
        member = member or ctx.author
        await self._send_stats(ctx, period, member)

    @commands.command('guild-stats')
    async def _send_guild_stats(self, ctx: commands.Context, period: PeriodConverter = TOTAL):
        await self._send_stats(ctx, period)

    async def _send_stats(self, ctx: commands.Context, period: PeriodConverter = TOTAL, member: discord.User = None):
        dt = time.time()
        top10 = await self._get_top10(period, ctx.guild.id, member)
        lang = await self.backend.get_guild_lang(ctx.guild.id)
        if period == self.TOTAL:
            if member is None:
                title = self.__cfg.i18n.get(lang, 'stats:guild_total', ctx.guild.name)
            else:
                title = self.__cfg.i18n.get(lang, 'stats:user_total', ctx.author.display_name)
        else:
            period_str = self.PERIOD_DESCRIPTION.get(period)
            if member is None:
                title = self.__cfg.i18n.get(lang, 'stats:guild_period', (ctx.guild.name, period_str))
            else:
                title = self.__cfg.i18n.get(lang, 'stats:user_period', (ctx.guild.name, period_str))

        msg = ''
        for e in top10:
            if e.emoji.is_custom:
                msg += str(self.bot.get_emoji(e.emoji.emoji_id))
            else:
                msg += e.emoji.unicode_char
            msg += f'\t— {e.total_mentions} mentions, {round(e.percentage)}%\n'

        dt = time.time() - dt
        embed = ds_utils.create_embed(
            title=title,
            description=msg,
            td=dt,
            thumbnail=None if member is None else member.avatar_url
        )
        await ctx.send(embed=embed)

    async def _get_top10(self, period: PeriodConverter, guild_id: int, member: discord.Member = None):
        member_id = member.id if member is not None else None
        if period == self.TOTAL:
            return await self.backend.get_emojis_top10(guild_id, member_id)
        elif period == self.YEARLY:
            return await self.backend.get_emojis_top10_yearly(guild_id, member_id)
        elif period == self.MONTHLY:
            return await self.backend.get_emojis_top10_monthly(guild_id, member_id)
        elif period == self.WEEKLY:
            return await self.backend.get_emojis_top10_weekly(guild_id, member_id)
        elif period == self.DAILY:
            return await self.backend.get_emojis_top10_daily(guild_id, member_id)
        else:
            raise ValueError('Invalid period type')

    #endregion

    #region config commands

    @commands.command('today')
    async def _today(self, ctx: commands.Context):
        tz = await self.backend.get_guild_tz(ctx.guild.id)
        lang = await self.backend.get_guild_lang(ctx.guild.id)
        date_fmt = self.__cfg.i18n.get(lang, 'today:date_fmt')
        try:
            now = datetime.now(tz).strftime(date_fmt)
        except:
            now = 'invalid date format'
        embed = ds_utils.create_embed(
            title=self.__cfg.i18n.get(lang, 'today:title'),
            description=self.__cfg.i18n.get(lang, 'today:description', {'tz': tz.tzname(None), 'now': now})
        )
        await ctx.send(embed=embed)


    #endregion
