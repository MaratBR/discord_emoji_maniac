from emoji_maniac.bot.bot import Command, CommandContext


class PingCommand(Command):
    default_name = 'ping'

    async def execute(self, ctx: CommandContext):
        await ctx.message.channel.send(f'{ctx.message.author.mention} PONG!')


class GetGuildStatsCommand(Command):
    default_name = 'guild-stats'

    async def execute(self, ctx: CommandContext):
        result = await ctx.parent.backend.get_emojis_global_top10(ctx.message.guild.id)
        msg = f'{ctx.message.author.mention} Here is the results:\n'
        for e in result:
            if e.emoji.is_custom:
                msg += str(ctx.parent.client.get_emoji(e.emoji.emoji_id))
            else:
                msg += e.emoji.unicode
            msg += f' - {e.total_mentions} mentions, {round(e.percentage)}%\n'
        await ctx.message.channel.send(msg)
