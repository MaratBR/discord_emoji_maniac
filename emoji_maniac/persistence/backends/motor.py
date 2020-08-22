import typing
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import base64
import struct
import emoji

from emoji_maniac.bot.config import Config
from emoji_maniac.persistence.emoji_backend import EmojiBackend, EmojiSource, Emoji, MessageEmoji
from emoji_maniac.persistence.models import StatsEmoji
from emoji_maniac.persistence.utils import pack2b64

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


class MotorEmojiBackend(EmojiBackend):

    motor_client: mas.AsyncIOMotorClient
    _cfg: MotorConfig
    _db_name: str
    _db: mas.AsyncIOMotorDatabase
    _emojis_collection: mas.AsyncIOMotorCollection

    def __init__(self, config: Config):
        super(MotorEmojiBackend, self).__init__(config)
        self._cfg = config.require_backend_config_as('motor', MotorConfig)
        self.log.info(f'MongoDB uri = {self._cfg.uri}, dbname = {self._cfg.dbname}')
        self.motor_client = mas.AsyncIOMotorClient(self._cfg.uri)
        self._db = self.motor_client[self._cfg.dbname]
        self._emojis_collection = self._db.discord_emojies

    async def submit_emoji(self, source: EmojiSource, emoji_obj: MessageEmoji):
        record = EmojiEntry.create(source, emoji_obj)
        await self._emojis_collection.insert_one(asdict(record))

    async def remove_emoji_source(self, source: EmojiSource):
        await self._emojis_collection.delete_many({'src_uid': source.uid})

    async def remove_emoji(self, source: EmojiSource, emoji_obj: Emoji):
        await self._emojis_collection.delete_many({
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
        result = self._emojis_collection.aggregate(pipeline)
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
