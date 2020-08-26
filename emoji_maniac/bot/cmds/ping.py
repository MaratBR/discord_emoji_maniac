from emoji_maniac.bot.bot import Command, CommandContext


class PingCommand(Command):
    default_name = 'ping'

    async def execute(self, ctx: CommandContext):
        await ctx.message.channel.send(f'{ctx.message.author.mention} :ping_pong:')
