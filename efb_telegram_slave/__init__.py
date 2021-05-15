import asyncio
import logging
from typing import Dict, Any, BinaryIO, Optional, Collection

import yaml

from ehforwarderbot import Message as EfbMsg, MsgType, Status, Chat, coordinator
from ehforwarderbot.channel import SlaveChannel
from ehforwarderbot.types import MessageID, ModuleID, InstanceID, ChatID
from ehforwarderbot.message import Message
from ehforwarderbot import utils as efb_utils
from ehforwarderbot.chat import GroupChat, PrivateChat, ChatMember
from ehforwarderbot.exceptions import EFBChatNotFound

from telethon import events
from telethon.events import NewMessage
from telethon.tl.types import User as TgUser, Chat as TgChat, Channel as TgChannel, PeerUser, PeerChat, PeerChannel
from telethon.tl.custom.message import Message as TgMsg
from telethon import TelegramClient

from .__version__ import __version__


def get_chat_id(msg: TgMsg) -> int:
    if isinstance(msg.peer_id, PeerUser):
        return msg.peer_id.user_id
    elif isinstance(msg.peer_id, PeerChat):
        return msg.peer_id.chat_id
    elif isinstance(msg.peer_id, PeerChannel):
        return msg.peer_id.channel_id


def print_color(text):
    print(f'\x1b[32m{text}\x1b[0m')


class TelegramChannel(SlaveChannel):
    channel_name = 'Telegram Slave'
    channel_emoji = '✈️'
    channel_id = ModuleID('sharzy.telegram')

    __version__ = __version__

    supported_message_types = {MsgType.Text}

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

    def load_config(self):
        config_path = efb_utils.get_config_path(self.channel_id)
        if not config_path.exists():
            return
        with config_path.open() as f:
            d = yaml.full_load(f)
            if not d:
                return
            self.config: Dict[str, Any] = d

    def make_chat(self, diag) -> Chat:
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
                if chat_uid == diag.entity.id:
                    chat = self.make_chat(diag)
            if chat is None:
                raise EFBChatNotFound()
            self.get_chat_cache[chat_uid] = chat
            return chat

    async def async_get_chats(self) -> Collection['Chat']:
        chats = []
        async for diag in self.client.iter_dialogs():
            chats.append(self.make_chat(diag))
        return chats

    def get_chats(self) -> Collection['Chat']:
        return self.loop.run_until_complete(self.async_get_chats())

    def get_chat(self, chat_uid: ChatID) -> 'Chat':
        return self.loop.run_until_complete(self.async_get_chat(chat_uid))

    def send_message(self, msg: 'EfbMsg') -> 'EfbMsg':
        asyncio.run_coroutine_threadsafe(self.client.send_message(int(msg.chat.uid), msg.text), self.loop).result()
        return msg

    def poll(self):
        @self.client.on(events.NewMessage())
        async def handleMsg(event: NewMessage):
            msg: TgMsg = event.message
            print(msg)
            chat_id = get_chat_id(msg)
            chat = await self.async_get_chat(chat_id)
            chat_member = ChatMember(
                chat=chat,
                name='Foo',
                uid=str(chat_id)
            )
            efb_msg = Message(
                deliver_to=coordinator.master,
                author=chat_member,
                chat=chat,
                text=msg.text,
                type=MsgType.Text,
                uid=f'{chat_id}-{msg.id}',
            )
            coordinator.send_message(efb_msg)

        self.loop.run_forever()

    def send_status(self, status: 'Status'):
        pass

    def stop_polling(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.client.disconnect()

    def get_message_by_id(self, chat: 'Chat', msg_id: MessageID) -> Optional['Message']:
        pass

    def get_chat_picture(self, chat: 'Chat') -> BinaryIO:
        pass
