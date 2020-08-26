from emoji_maniac.bot.bot import ModuleBase, Bot
from emoji_maniac.bot.commands import *


class DefaultModule(ModuleBase):
    def get_description(self) -> str:
        return 'Default module with basic commands'

    def get_display_name(self) -> str:
        return 'Default module'

    def __init__(self, bot: Bot):
        super(DefaultModule, self).__init__(bot)
        self.register_command(PingCommand)
        self.register_command(GetStatsCommand)
        self.register_command(RandomEmojiCommand)
