import random

import emoji

from emoji_maniac.bot.bot import Command, CommandContext


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