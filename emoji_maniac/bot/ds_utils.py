import asyncio
import time
from datetime import timedelta, datetime

import discord as discord


def create_embed(title: str = None, description: str = None, from_cache: bool = False, thumbnail: str = None,
                color: int = 0xffff00, ts = None, td = None, footer: str = None):
    if footer is None:
        footer = []
        if td is not None:
            if isinstance(td, timedelta):
                td = td.total_seconds()
            td = round(td * 1000)
            footer.append(f'{td}ms')
        if from_cache:
            footer.append('(from cache)')
        footer = ' '.join(footer)
    embed = discord.Embed(
        timestamp=ts or datetime.utcnow(),
        title=title,
        color=discord.Colour(color),
        description=description
    )
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text=footer)
    return embed


async def _time_measure_wrapper(coro):
    starts_at = time.time()
    result = await coro
    dt = time.time() - starts_at
    return result, dt


async def took_too_long_message_utility(channel: discord.TextChannel, *, coro, handler, ttl_msg, timeout: float = 3, ttl_title: str = None):

    sleep_result = object()
    finished, unfinished = await asyncio.wait([
        asyncio.sleep(timeout, result=sleep_result),
        _time_measure_wrapper(coro)
    ], return_when=asyncio.FIRST_COMPLETED)
    result = tuple(finished)[0].result()
    if result == sleep_result:
        # Operation took too long
        embed = create_embed(
            title=ttl_title,
            description=ttl_msg,
        )
        message = await channel.send(embed=embed)
        results, _ = await asyncio.wait(unfinished)
        result, dt = tuple(results)[0].result()
        result = handler(result, dt)
        if isinstance(result, discord.Embed):
            await message.edit(embed=result)
        elif isinstance(result, str):
            await message.edit(content=result)
        else:
            await message.delete()
    else:
        result, dt = result
        result = handler(result, dt)
        if isinstance(result, discord.Embed):
            await channel.send(embed=result)
        elif isinstance(result, str):
            await channel.send(content=result)

