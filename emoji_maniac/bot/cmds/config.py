from datetime import datetime

from emoji_maniac.bot import ds_utils
from emoji_maniac.bot.bot import Command, CommandContext


class ConfigCommand(Command):
    default_name = 'storage'

    TITLE_CURRENT_DATE = 'What a beautiful day, today is!'

    async def execute(self, ctx: CommandContext):
        type_ = ctx.get_arg(0)
        if type_ == 'date':
            await self.send_date(ctx)
        else:
            config = await ctx.parent.backend.get_guild_config(ctx.message.guild.id)
            if config:
                del config['_id']
            import json
            await ctx.message.channel.send(f'```json\n{json.dumps(config, indent=4, default=str)}\n```')

    @classmethod
    async def send_date(cls, ctx: CommandContext):
        tz = await ctx.parent.backend.get_guild_tz(ctx.message.guild.id)
        now = datetime.now(tz).strftime('%B %d, %Y, %A %X')
        embed = ds_utils.create_embed(
            title=cls.TITLE_CURRENT_DATE,
            description=f':calendar: I configured with timezone `{tz.tzname(None)}`, so IMO today is `{now}`.\n '
                        f'Have a good day and smile more :slight_smile:'
        )
        await ctx.message.channel.send(embed=embed)


class TodayCommand(Command):
    default_name = 'today'

    async def execute(self, ctx: CommandContext):
        await ConfigCommand.send_date(ctx)
