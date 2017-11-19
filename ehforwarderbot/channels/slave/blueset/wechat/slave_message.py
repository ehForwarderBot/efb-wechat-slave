import logging
import re
import tempfile
import uuid
from typing import TYPE_CHECKING, Callable

import magic
import os
import xmltodict

from ehforwarderbot import EFBMsg, MsgType, EFBChat, coordinator
from ehforwarderbot.status import EFBMessageRemoval
from ehforwarderbot.message import EFBMsgLocationAttribute, EFBMsgLinkAttribute
from . import wxpy
from .wxpy.api import consts
from . import constants

if TYPE_CHECKING:
    from . import WeChatChannel


class SlaveMessageManager:

    def __init__(self, channel: 'WeChatChannel'):
        self.channel: 'WeChatChannel' = channel
        self.bot: wxpy.Bot = channel.bot
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.wechat_msg_register()

    class Decorators:
        @classmethod
        def wechat_msg_meta(cls, func: Callable):
            def wrap_func(self: 'SlaveMessageManager', msg: wxpy.Message, *args, **kwargs):
                logger = logging.getLogger("__name__")
                logger.debug("[%s] Raw message: %r", msg.id, msg.raw)

                efb_msg: EFBMsg = func(self, msg, *args, **kwargs)

                if efb_msg is None:
                    return

                efb_msg.uid = getattr(msg, "id", constants.INVALID_MESSAGE_ID + str(uuid.uuid4()))

                chat: EFBChat = self.channel.chats.wxpy_chat_to_efb_chat(msg.chat)

                author: EFBChat = self.channel.chats.wxpy_chat_to_efb_chat(msg.sender)

                # Do not override what's defined in the sub-functions
                efb_msg.chat = efb_msg.chat or chat
                efb_msg.author = efb_msg.chat or author

                logger.debug("[%s] Chat: %s, Author: %s", efb_msg.uid, efb_msg.chat, efb_msg.author)

                efb_msg.deliver_to = coordinator.master

                coordinator.send_message(efb_msg)
                if efb_msg.file:
                    efb_msg.file.close()

            return wrap_func

    def wechat_msg_register(self):
        self.bot.register(msg_types=consts.TEXT)(self.wechat_text_msg)
        self.bot.register(msg_types=consts.SHARING)(self.wechat_link_msg)
        self.bot.register(msg_types=consts.PICTURE)(self.wechat_picture_msg)
        self.bot.register(msg_types=consts.ATTACHMENT)(self.wechat_file_msg)
        self.bot.register(msg_types=consts.RECORDING)(self.wechat_voice_msg)
        self.bot.register(msg_types=consts.MAP)(self.wechat_location_msg)
        self.bot.register(msg_types=consts.VIDEO)(self.wechat_video_msg)
        self.bot.register(msg_types=consts.CARD)(self.wechat_card_msg)
        self.bot.register(msg_types=consts.FRIENDS)(self.wechat_friend_msg)
        self.bot.register(msg_types=consts.NOTE)(self.wechat_system_msg)

        @self.bot.register(msg_types=consts.SYSTEM)
        def wc_msg_system_log(msg):
            self.logger.debug("WeChat System Message:\n%s", repr(msg))

    @Decorators.wechat_msg_meta
    def wechat_text_msg(self, msg: wxpy.Message):
        if msg.chat.user_name == "newsapp" and msg.text.startswith("<mmreader>"):
            self.wechat_newsapp_msg(msg)
            return
        if msg.text.startswith("http://weixin.qq.com/cgi-bin/redirectforward?args="):
            self.wechat_location_msg(msg)
            return
        efb_msg = EFBMsg()
        efb_msg.text = msg.text
        efb_msg.type = MsgType.Text
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_system_msg(self, msg: wxpy.Message):
        if msg.recalled_message_id:
            efb_msg = EFBMsg()
            efb_msg.chat = self.channel.chats.wxpy_chat_to_efb_chat(msg.chat)
            efb_msg.author = self.channel.chats.wxpy_chat_to_efb_chat(msg.sender)
            efb_msg.uid = str(msg.recalled_message_id)
            coordinator.send_status(EFBMessageRemoval(source_channel=self.channel,
                                                      destination_channel=coordinator.master,
                                                      message=efb_msg))
            return
        efb_msg = EFBMsg()
        efb_msg.text = msg.text
        efb_msg.type = MsgType.Text
        efb_msg.author = EFBChat(self).system()
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_location_msg(self, msg: wxpy.Message):
        efb_msg = EFBMsg()
        efb_msg.text = msg.text.split('\n')[0][:-1]
        # loc = re.search("=-?([0-9.]+),-?([0-9.]+)", msg.url).groups()
        # efb_msg.attributes = EFBMsgLocationAttribute(longitude=float(loc[1]), latitude=float(loc[0]))
        efb_msg.attributes = EFBMsgLocationAttribute(longitude=msg.location['x'], latitude=msg.location['y'])
        efb_msg.type = MsgType.Location
        return efb_msg

    def wechat_link_msg(self, msg: wxpy.Message):
        # parse XML
        links = msg.articles
        if self.channel.flag("first_link_only"):
            links = links[:1]
        for i in links:
            self.wechat_raw_link_msg(i.title, i.summary, i.cover, i.url)
        return

    @Decorators.wechat_msg_meta
    def wechat_raw_link_msg(self, title, description, image, url):
        efb_msg = EFBMsg()
        if url:
            efb_msg.type = MsgType.Link
            efb_msg.attributes = EFBMsgLinkAttribute(
                title=title,
                description=description,
                image=image,
                url=url
            )
        else:
            efb_msg.type = MsgType.Text
            efb_msg.text = "%s\n%s" % (title, description)
            if image:
                efb_msg.text += "\n\n%s" % image
        return efb_msg

    def wechat_newsapp_msg(self, msg: wxpy.Message):
        data = xmltodict.parse(msg.text)
        news = data.get('mmreader', {}).get('category', {}).get('newitem', [])
        if news:
            self.wechat_raw_link_msg(msg, news[0]['title'], news[0]['digest'], news[0]['cover'], news[0]['shorturl'])
            if self.channel.flag("extra_links_on_message"):
                for i in news[1:]:
                    self.wechat_raw_link_msg(msg, i['title'], i['digest'], i['cover'], i['shorturl'])

    @Decorators.wechat_msg_meta
    def wechat_picture_msg(self, msg: wxpy.Message):
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.Image if msg.raw['MsgType'] == 3 else MsgType.Sticker
        try:
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.text = ""
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += "[无法接收此消息，请转到手机微信查看]"
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_file_msg(self, msg: wxpy.Message):
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.File
        try:
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.text = msg.file_name or ""
            efb_msg.filename = msg.file_name or ""
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += "[无法接收此消息，请转到手机微信查看]"
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_voice_msg(self, msg: wxpy.Message):
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.Audio
        try:
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.text = ""
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += "[无法接收此消息，请转到手机微信查看]"
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_video_msg(self, msg: wxpy.Message):
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.Video
        try:
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.text = ""
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += "[无法接收此消息，请转到手机微信查看]"
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_card_msg(self, msg: wxpy.Message):
        efb_msg = EFBMsg()
        txt = ("Name card: {user.nick_name}\n"
               "From: {user.province}, {user.city}\n"
               "Signature: {user.signature}\n"
               "Gender: {user.sex}")
        txt = txt.format(user=msg.card)
        efb_msg.text = txt
        efb_msg.type = MsgType.Command
        efb_msg.attributes = {
            "commands": [
                {
                    "name": "Send friend request",
                    "callable": "add_friend",
                    "args": [],
                    "kwargs": {
                        "username": msg.card.user_name
                    }
                }
            ]
        }
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_friend_msg(self, msg: wxpy.Message):
        efb_msg = EFBMsg()
        txt = ("Name card: {user.nick_name}\n"
               "From: {user.province}, {user.city}\n"
               "Signature: {user.signature}\n"
               "Gender: {user.sex}")
        txt = txt.format(user=msg.card)
        efb_msg.text = txt
        efb_msg.type = MsgType.Command
        efb_msg.attributes = {
            "commands": [
                {
                    "name": "Send friend request",
                    "callable": "accept_friend",
                    "args": [],
                    "kwargs": {
                        "username": msg.card.user_name
                    }
                }
            ]
        }
        return efb_msg

    @staticmethod
    def save_file(msg: wxpy.Message):
        file = tempfile.NamedTemporaryFile()
        msg.get_file(file.name)
        if os.fstat(file.fileno()).st_size <= 0:
            raise EOFError('File downloaded is Empty')
        file.seek(0)
        mime = magic.from_file(file.name, mime=True)
        if isinstance(mime, bytes):
            mime = mime.decode()
        return file.path, mime, file
