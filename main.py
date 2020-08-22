from emoji_maniac import *
from emoji_maniac.bot.commands import PingCommand, GetGuildStatsCommand
from emoji_maniac.persistence.backends.motor import MotorEmojiBackend

set_debug(True)
bot = Bot(MotorEmojiBackend)
bot.register_command(PingCommand)
bot.register_command(GetGuildStatsCommand)
bot.run()
