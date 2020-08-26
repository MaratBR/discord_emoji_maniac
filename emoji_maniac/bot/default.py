import typing

from emoji_maniac import Bot, set_debug
from emoji_maniac.persistence.emoji_backend import EmojiBackend


def create_bot(backend: typing.Type[EmojiBackend]):
    return Bot(backend)


def run_default(debug: bool = False):
    if debug:
        set_debug(True)
    from emoji_maniac.persistence.backends.motor import MotorEmojiBackend
    create_bot(MotorEmojiBackend).run()
