from discord.ext import commands


class WordWithAutoComplete(commands.Converter):
    def __init__(self, word: str):
        self.word = word

    async def convert(self, ctx: commands.Context, argument: str):
        argument = argument.lower().strip()
        return self.word.startswith(argument)
