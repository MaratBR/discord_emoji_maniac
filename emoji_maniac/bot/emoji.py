import discord
import emoji
import re
import typing

from emoji_maniac.persistence.emoji_backend import MessageEmoji

regex = re.compile(r'<:(\w+):(\d+)>')


def get_emojis(text: str) -> typing.List[MessageEmoji]:
    emoji_unicode = [c for c in text if c in emoji.UNICODE_EMOJI]
    emoji_count = {}

    for em in emoji_unicode:
        c = emoji_count.get(em)
        if c is not None:
            emoji_count[em] = emoji_count[em] + 1
        else:
            emoji_count[em] = 1

    emojis_list = [
        MessageEmoji.unicode(emoji.UNICODE_EMOJI[c][1:-1], emoji_count[c])
        for c in emoji_count.keys() if c in emoji.UNICODE_EMOJI]
    match = regex.findall(text)
    if match:
        custom_emojis_count = {}
        for g in match:
            name = g[0]
            emoji_id = int(g[1])
            key = (emoji_id, name)
            c = custom_emojis_count.get(key)
            if c is None:
                custom_emojis_count[key] = 1
            else:
                custom_emojis_count[key] = custom_emojis_count[key] + 1

        for (emoji_id, name), count in custom_emojis_count.items():
            emojis_list.append(MessageEmoji.custom(name, emoji_id, count))
    return emojis_list

