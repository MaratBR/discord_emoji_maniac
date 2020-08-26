import asyncio
import pickle
import typing
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from itertools import product
from math import ceil

import emoji
import discord
from pymongo import UpdateOne

from emoji_maniac.bot.config import Config
from emoji_maniac.persistence.emoji_backend import EmojiBackend, EmojiSource, Emoji, MessageEmoji
from emoji_maniac.persistence.models import StatsEmoji

try:
    import motor.motor_asyncio as mas
except Exception as e:
    print('Please install motor library -> pip install motor')
    raise e


DEFAULT_MONGODB_URI = 'mongodb://localhost:27017'
DEFAULT_MONGODB_NAME = 'emoji_maniac'


@dataclass
class MotorConfig:
    uri: str = DEFAULT_MONGODB_URI
    dbname: str = DEFAULT_MONGODB_NAME


@dataclass
class EmojiEntry:
    gld_id: int
    msg_id: int
    usr_id: int
    src_uid: str
    count: int
    is_reaction: bool
    emoji_uid: str

    at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, source: EmojiSource, emoji_obj: MessageEmoji) -> 'EmojiEntry':
        return EmojiEntry(
            gld_id=source.guild_id,
            usr_id=source.user_id,
            msg_id=source.message_id,
            src_uid=source.uid,
            count=emoji_obj.count,
            emoji_uid=emoji_obj.uid,
            is_reaction=source.reaction
        )


class _Counters:
    @staticmethod
    def _week_number_util(dt):
        first_day = dt.replace(day=1)

        dom = dt.day
        adjusted_dom = dom + first_day.weekday()

        return int(ceil(adjusted_dom / 7.0))

    @classmethod
    def period_modifiers(cls):
        now = datetime.utcnow()
        year = str(now.year)
        month = str(now.year * 100 + now.month)
        week = str(now.year * 1000 + now.month * 10 + cls._week_number_util(now))
        day = str(now.year * 10000 + now.month * 100 + now.day)
        return 'total', year, month, week, day

    @staticmethod
    def year_modifier():
        return str(datetime.utcnow().year)

    @staticmethod
    def month_modifier():
        now = datetime.utcnow()
        return str(now.year * 100 + now.month)

    @classmethod
    def week_modifier(cls):
        now = datetime.utcnow()
        return str(now.year * 1000 + now.month * 10 + cls._week_number_util(now))

    @staticmethod
    def day_modifier():
        now = datetime.utcnow()
        return str(now.year * 10000 + now.month * 100 + now.day)

    @classmethod
    def guild_counters(cls, guild_id: int):
        return [
            f'g{guild_id}_' + item
            for item in cls.period_modifiers()
        ]

    @classmethod
    def user_counters(cls, guild_id: int, user_id: int):
        return [
            f'u{guild_id}-{user_id}_' + item
            for item in cls.period_modifiers()
        ]

    @classmethod
    def emoji_counters(cls, emoji_uid: str, guild_id: int):
        return [(f'{emoji_uid}-{guild_id}', mod) for mod in cls.period_modifiers()]


class MotorEmojiBackend(EmojiBackend):
    motor_client: mas.AsyncIOMotorClient
    _cfg: MotorConfig
    _db_name: str
    _db: mas.AsyncIOMotorDatabase

    def __init__(self, config: Config):
        super(MotorEmojiBackend, self).__init__(config)
        self._cfg = config.require_backend_config_as('motor', MotorConfig)
        self.log.info(f'MongoDB uri = {self._cfg.uri}, dbname = {self._cfg.dbname}')
        self.motor_client = mas.AsyncIOMotorClient(self._cfg.uri)
        self._db = self.motor_client[self._cfg.dbname]

    async def init(self):
        pass

    async def submit_reaction(self, guild_id: int, message_id: int, user_id: int, emoji_obj: Emoji):
        # Increment counters
        counters = _Counters.guild_counters(guild_id) + _Counters.user_counters(guild_id, user_id)
        await self._update_guild_counters(counters, {emoji_obj.uid: 1})

        # Increment per-emoji counters
        await self._increment_emoji_counters(guild_id, user_id, {emoji_obj.uid: 1})

    async def _increment_emoji_counters(self, guild_id: int, user_id: int, emojis: typing.Dict[str, int]):
        updates = []
        for (emoji_uid, hits) in emojis.items():
            updates = [
                UpdateOne(
                    {'usr_id': user_id, 'emoji_uid': emoji_uid, 'gld_id': guild_id, 'period': period},
                    {'$inc': {'hits': hits}}, upsert=True)
                for period in _Counters.period_modifiers()
            ]
        await self._db.ds_emoji_counters.bulk_write(updates)

    async def _increment_multiple_emoji_counters(self, counters: typing.List[str], value: int):
        await self._db.ds_emoji_counters.bulk_write([
            UpdateOne({'_id': name}, {'$inc': {'hits': value}}, upsert=True) for name in counters
        ])

    async def _update_guild_counters(self, names: typing.Union[str, typing.List[str]], values: dict):
        if isinstance(names, str):
            # We have only one counter to update
            await self._db.ds_emoji_gld_counters.update_many({'_id': names}, {
                '$inc': values
            }, upsert=True)
        else:
            # 2+ counter, bulk operation
            await self._db.ds_emoji_gld_counters.bulk_write([
                UpdateOne({'_id': name}, {'$inc': values}, upsert=True) for name in names
            ])

    async def remove_reaction(self, guild_id: int, message_id: int, user_id: int, emoji_obj: Emoji):
        # Decrement counters
        counters = _Counters.guild_counters(guild_id) + _Counters.user_counters(guild_id, user_id)
        await self._update_guild_counters(counters, {emoji_obj.uid: -1})

        # Decrement per-emoji counters
        await self._increment_emoji_counters(guild_id, user_id, {emoji_obj.uid: 1})

    async def submit_message(self, message: discord.Message, emojis: typing.List[MessageEmoji]):
        guild_id = message.guild.id
        user_id = message.author.id
        counters = _Counters.guild_counters(guild_id) + _Counters.user_counters(guild_id, user_id)
        values = {em.uid: em.count for em in emojis}
        await self._update_guild_counters(counters, values)

        # Increment per-emoji counters
        await self._increment_emoji_counters(guild_id, user_id, {m.uid: m.count for m in emojis})

    @staticmethod
    def _top_match(period: str, guild_id: int, user_id: int = None):
        match = {
            'gld_id': guild_id,
            'period': period
        }
        if user_id is not None:
            match['usr_id'] = user_id
        return match

    async def _get_emojis_top10(self, guild_id: int, user_id: int, period: str):
        return self._make_emojis_top(
            await self._db.ds_emoji_counters.find(
                self._top_match(period, guild_id, user_id),
                sort=[('hits', -1)], limit=10).to_list(None)
        )

    async def get_emojis_top10(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        return await self._get_emojis_top10(guild_id, user_id, 'total')

    async def get_emojis_top10_yearly(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        return await self._get_emojis_top10(guild_id, user_id, _Counters.year_modifier())

    async def get_emojis_top10_monthly(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        return await self._get_emojis_top10(guild_id, user_id, _Counters.month_modifier())

    async def get_emojis_top10_weekly(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        return await self._get_emojis_top10(guild_id, user_id, _Counters.week_modifier())

    async def get_emojis_top10_daily(self, guild_id: int, user_id: int = None) -> typing.List[StatsEmoji]:
        return await self._get_emojis_top10(guild_id, user_id, _Counters.day_modifier())

    @staticmethod
    def _make_emojis_top(values: typing.List[dict]) -> typing.List[StatsEmoji]:
        results = []
        for d in values:
            uid = d.get('emoji_uid')
            hits = d.get('hits')
            if uid is None or hits is None:
                # TODO Warning to log
                continue
            results.append(
                StatsEmoji(emoji=Emoji.from_uid(uid), total_mentions=hits, percentage=0)
            )
        total = sum(s.total_mentions for s in results)
        for s in results:
            s.percentage = s.total_mentions / total * 100
        return results

    async def submit_emoji(self, source: EmojiSource, emoji_obj: MessageEmoji):
        record = EmojiEntry.create(source, emoji_obj)
        await self._db.ds_emojies.insert_one(asdict(record))

    async def remove_emoji_source(self, source: EmojiSource):
        await self._db.ds_emojies.delete_many({'src_uid': source.uid})

    async def submit_bulk(self, records: typing.List[typing.Tuple[EmojiSource, MessageEmoji]]):
        records = [EmojiEntry.create(s, e) for (s, e) in records]
        records = list(asdict(r) for r in records)
        await self._db.ds_emojies.insert_many(records)

    async def remove_emoji(self, source: EmojiSource, emoji_obj: Emoji):
        await self._db.ds_emojies.delete_many({
            'src_uid': source.uid,
            'is_reaction': source.reaction,
            'emoji_uid': emoji_obj.uid
        })

    async def get_emojis_top(self, guild_id: int = None, last_n_days: int = None,
                             user_id: int = None, limit: int = None) -> typing.List[StatsEmoji]:
        pipeline = []
        if not (guild_id is None and last_n_days is None and user_id is None):
            match = {}
            if guild_id is not None:
                match['gld_id'] = guild_id
            if user_id is not None:
                match['usr_id'] = user_id
            if last_n_days is not None:
                match['at'] = {
                    '$gt': datetime.utcnow() - timedelta(days=last_n_days)
                }
            pipeline.append({'$match': match})
        pipeline.append({
            '$group': {
                '_id': '$emoji_uid',
                'count': {
                    '$sum': '$count'
                }
            }
        })
        pipeline.append({
            '$sort': {
                'count': -1
            }
        })
        if limit is not None:
            limit = max(limit, 1)
            pipeline.append({
                '$limit': limit
            })
        result = self._db.ds_emojies.aggregate(pipeline)
        stats = []
        async for doc in result:
            id_ = doc['_id']
            emoji_obj = Emoji.from_uid(id_)
            if emoji_obj is None:
                self.log.error(f'Failed to decode emoji id = "{id_}"')
                continue
            stats.append(StatsEmoji(emoji=emoji_obj, total_mentions=doc.get('count'), percentage=0))
        total = sum(r.total_mentions for r in stats)
        for r in stats:
            r.percentage = r.total_mentions / total * 100
        return stats

    async def put_cache(self, key: str, value, age: timedelta = timedelta(minutes=10)):
        if not self.config.cache_cfg.enabled:
            return

        await self._db.ds_cache.update_one({
            '_id': key
        }, {
            '$set': {
                'value': pickle.dumps(value),
                'expires_at': datetime.utcnow() + age
            }
        }, upsert=True)

    async def get_cache(self, key: str):
        if not self.config.cache_cfg.enabled:
            return None
        record = await self._db.ds_cache.find_one({'_id': key})
        if record is None:
            return None
        try:
            value = pickle.loads(record['value'])
            return value
        except Exception as exc:
            self.log.error('Failed to load cache: ' + str(exc))
            return None

    async def clear_cache(self):
        await self._db.ds_cache.delete_many({})
