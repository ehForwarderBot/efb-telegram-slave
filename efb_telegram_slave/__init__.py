import asyncio
import logging
from typing import Dict, Any, BinaryIO, Optional, Collection
import io
import threading
import tempfile

import yaml

from ehforwarderbot import Message as EfbMsg, MsgType, Status, Chat, coordinator
from ehforwarderbot.channel import SlaveChannel
from ehforwarderbot.types import MessageID, ModuleID, InstanceID, ChatID
from ehforwarderbot.message import Message
from ehforwarderbot import utils as efb_utils
from ehforwarderbot.chat import GroupChat, PrivateChat, ChatMember
from ehforwarderbot.exceptions import EFBChatNotFound, EFBOperationNotSupported

from telethon import events
from telethon.events import NewMessage
from telethon.tl.types import User as TgUser, Chat as TgChat, Channel as TgChannel, PeerUser, PeerChat, PeerChannel, \
    MessageMediaPhoto, MessageMediaDocument, \
    DocumentAttributeSticker, DocumentAttributeFilename, DocumentAttributeVideo, DocumentAttributeAudio
from telethon.tl.custom.message import Message as TgMsg
from telethon import TelegramClient
from telethon.utils import get_extension

from .__version__ import __version__


def get_chat_id(peer) -> int:
    if isinstance(peer, PeerUser):
        return peer.user_id
    elif isinstance(peer, PeerChat):
        return peer.chat_id
    elif isinstance(peer, PeerChannel):
        return peer.channel_id
    else:
        raise ValueError(f'Unknown chat {peer}')


def format_entity_name(entity):
    if isinstance(entity, TgUser):
        first_name = entity.first_name or ''
        last_name = entity.last_name or ''
        return (first_name + ' ' + last_name).strip()
    elif isinstance(entity, TgChat) or isinstance(entity, TgChannel):
        return entity.title
    else:
        raise ValueError(f'Unknown entity {entity}')


def print_color(text):
    print(f'\x1b[32m{text}\x1b[0m')


class TelegramChannel(SlaveChannel):
    channel_name = 'Telegram Slave'
    channel_emoji = '✈️'
    channel_id = ModuleID('sharzy.telegram')

    __version__ = __version__

    supported_message_types = {
        MsgType.Text,
        MsgType.Image,
        MsgType.File,
        MsgType.Sticker,
        MsgType.Video,
        MsgType.Audio
    }

    logger: logging.Logger = logging.getLogger(f'plugins.{channel_id}.TelegramChannel')

    config: Dict[str, Any] = dict()

    def __init__(self, instance_id: InstanceID = None):
        super().__init__(instance_id)
        self.load_config()
        self.loop = asyncio.get_event_loop()
        data_path = efb_utils.get_data_path(self.channel_id)
        proxy = (self.config['proxy']['protocol'], self.config['proxy']['host'], self.config['proxy']['port'])
        self.client: TelegramClient = TelegramClient(f'{data_path}/{instance_id}',
                                                     self.config['api_id'],
                                                     self.config['api_hash'],
                                                     loop=self.loop,
                                                     proxy=proxy).start()
        self.get_chat_cache: Dict[str, ChatID] = {}
        self.task = None
        self._main_thread_name = threading.current_thread().name

    def load_config(self):
        config_path = efb_utils.get_config_path(self.channel_id)
        if not config_path.exists():
            return
        with config_path.open() as f:
            d = yaml.full_load(f)
            if not d:
                return
            self.config: Dict[str, Any] = d

    def make_efb_chat_obj(self, diag) -> Chat:
        if isinstance(diag.entity, TgUser):
            return PrivateChat(
                channel=self, name=diag.name, uid=str(diag.entity.id), other_is_self=diag.entity.is_self
            )
        if isinstance(diag.entity, TgChat) or isinstance(diag.entity, TgChannel):
            return GroupChat(
                channel=self, name=diag.name, uid=str(diag.entity.id)
            )

    async def async_get_chat(self, chat_uid: ChatID) -> Chat:
        cache = self.get_chat_cache.get(chat_uid, None)
        if cache:
            return cache
        else:
            chat = None
            async for diag in self.client.iter_dialogs():
                if int(chat_uid) == diag.entity.id:
                    chat = self.make_efb_chat_obj(diag)
            if chat is None:
                raise EFBChatNotFound()
            self.get_chat_cache[chat_uid] = chat
            return chat

    async def async_get_chats(self) -> Collection['Chat']:
        chats = []
        async for diag in self.client.iter_dialogs():
            chats.append(self.make_efb_chat_obj(diag))
        return chats

    def get_chats(self) -> Collection['Chat']:
        return self._async_run(self.async_get_chats())

    def get_chat(self, chat_uid: ChatID) -> 'Chat':
        return self._async_run(self.async_get_chat(chat_uid))

    def send_message(self, msg: 'EfbMsg') -> 'EfbMsg':
        if msg.file:
            print_color(f'{msg.text=}, {msg.uid=}, {msg.file.name}, {msg.file.fileno}')
        file = msg.file
        if hasattr(file, 'name'):
            # for file in file system, take its path as input
            # otherwise mimetype may be mistakenly guessed by telethon
            file = file.name
        self._async_run(
            self.client.send_message(int(msg.chat.uid), msg.text, file=file)
        )
        return msg

    def poll(self):
        @self.client.on(events.NewMessage())
        async def handleMsg(event: NewMessage):
            # because telethon swallows exceptions in handlers,
            # we need to add extra exception handler
            try:
                await self.handle_new_telegram_message(event)
            except Exception as e:
                self.logger.error(e)
                raise e

        self.loop.run_forever()

    def send_status(self, status: 'Status'):
        pass

    def stop_polling(self):
        self.loop.call_soon_threadsafe(self.loop.stop)

    def get_message_by_id(self, chat: 'Chat', msg_id: MessageID) -> Optional['Message']:
        raise EFBOperationNotSupported()

    def get_chat_picture(self, chat: 'Chat') -> BinaryIO:
        picture = io.BytesIO()
        chat_id = int(chat.uid)
        entity = self._async_run(self.client.get_entity(chat_id))
        self._async_run(self.client.download_profile_photo(entity, picture))
        return picture

    def _async_run(self, promise):
        # Warning: do not use this in async function
        if not self.loop.is_running():
            return self.loop.run_until_complete(promise)
        else:
            return asyncio.run_coroutine_threadsafe(promise, self.loop).result()

    async def handle_new_telegram_message(self, event: NewMessage):
        msg: TgMsg = event.message
        print_color(msg)
        chat_id = get_chat_id(msg.peer_id)
        chat = await self.async_get_chat(chat_id)

        file = None
        path = None
        filename = None
        mime = None
        msg_type = MsgType.Text
        tempfile_suffix = ''
        if getattr(msg, 'media', None):
            media = msg.media
            tempfile_suffix = get_extension(media)
            if isinstance(media, MessageMediaPhoto):
                msg_type = MsgType.Image
            if isinstance(media, MessageMediaDocument):
                document = media.document
                mime = document.mime_type
                msg_type = MsgType.File
                for attr in document.attributes:
                    if isinstance(attr, DocumentAttributeFilename):
                        tempfile_suffix = attr.file_name
                        filename = attr.file_name
                    if isinstance(attr, DocumentAttributeSticker):
                        msg_type = MsgType.Sticker
                    if isinstance(attr, DocumentAttributeVideo):
                        msg_type = MsgType.Video
                    if isinstance(attr, DocumentAttributeAudio):
                        msg_type = MsgType.Audio
        if msg_type != MsgType.Text:
            file = tempfile.NamedTemporaryFile(suffix=tempfile_suffix)
            path = file.name
            await self.client.download_media(msg, file)

        msg_peer = await self.client.get_entity(get_chat_id(msg.from_id or msg.peer_id))
        print(msg_peer)

        chat_member = ChatMember(
            chat=chat,
            name=format_entity_name(msg_peer),
            uid=str(chat_id),
        )
        efb_msg = Message(
            deliver_to=coordinator.master,
            author=chat_member,
            chat=chat,
            text=msg.message,
            type=msg_type,
            uid=f'{chat_id}_{msg.id}',
            file=file,
            filename=filename,
            mime=mime,
            path=path,
        )
        coordinator.send_message(efb_msg)
