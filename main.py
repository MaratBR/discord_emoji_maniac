from emoji_maniac import *
from emoji_maniac.bot.commands import PingCommand, GetStatsCommand, RandomEmojiCommand, PopulateCommand
from emoji_maniac.persistence.backends.motor import MotorEmojiBackend

set_debug(True)
bot = Bot(MotorEmojiBackend)
bot.register_command(PingCommand)
bot.register_command(GetStatsCommand)
bot.register_command(RandomEmojiCommand)
bot.register_command(PopulateCommand)
bot.run()
