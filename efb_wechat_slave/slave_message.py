import logging
import tempfile
import uuid
from typing import TYPE_CHECKING, Callable, Optional, Tuple, IO

import magic
import os

import itchat
import re
import requests
import xmltodict

from ehforwarderbot import EFBMsg, MsgType, EFBChat, coordinator
from ehforwarderbot.status import EFBMessageRemoval
from ehforwarderbot.message import EFBMsgLocationAttribute, EFBMsgLinkAttribute, EFBMsgCommands, EFBMsgCommand, \
    EFBMsgSubstitutions
from . import wxpy
from .wxpy.api import consts
from . import constants
from . import utils as ews_utils

if TYPE_CHECKING:
    from . import WeChatChannel


class SlaveMessageManager:

    UNSUPPORTED_MSG_PROMPT = (
        'This type of message is not supported on Web WeChat. View it on your phone.',
        'このタイプのメッセージはWeChatではサポートされていません。あなたの電話で見る。',
        '该类型暂不支持，请在手机上查看',
        '該類型暫不支持，請在手機上查看。',
        '暫時不支援該類型，請在手機上查看。',
        'ဤစာအမ်ိဳးအစားသည္ ဝက္ဘ္ WeChat တြင္ မေထာက္ပံ့ပါ။ ၄င္းကို သင့္ဖုန္းတြင္ ၾကည့္ပါ။',
    )

    def __init__(self, channel: 'WeChatChannel'):
        self.channel: 'WeChatChannel' = channel
        self.bot: wxpy.Bot = channel.bot
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.wechat_msg_register()

    class Decorators:
        @classmethod
        def wechat_msg_meta(cls, func: Callable):
            def wrap_func(self: 'SlaveMessageManager', msg: wxpy.Message, *args, **kwargs):
                logger = logging.getLogger(__name__)
                logger.debug("[%s] Raw message: %r", msg.id, msg.raw)

                efb_msg: EFBMsg = func(self, msg, *args, **kwargs)

                if efb_msg is None:
                    return

                efb_msg.uid = getattr(msg, "id", constants.INVALID_MESSAGE_ID + str(uuid.uuid4()))

                chat: EFBChat = self.channel.chats.wxpy_chat_to_efb_chat(msg.chat)

                author: EFBChat = self.channel.chats.wxpy_chat_to_efb_chat(msg.author)

                # Do not override what's defined in the sub-functions
                efb_msg.chat = efb_msg.chat or chat
                efb_msg.author = efb_msg.author or author

                logger.debug("[%s] Chat: %s, Author: %s", efb_msg.uid, efb_msg.chat, efb_msg.author)

                efb_msg.deliver_to = coordinator.master

                coordinator.send_message(efb_msg)
                if efb_msg.file:
                    efb_msg.file.close()

            return wrap_func

    def wechat_msg_register(self):
        self.bot.register(except_self=False, msg_types=consts.TEXT)(self.wechat_text_msg)
        self.bot.register(except_self=False, msg_types=consts.SHARING)(self.wechat_sharing_msg)
        self.bot.register(except_self=False, msg_types=consts.PICTURE)(self.wechat_picture_msg)
        self.bot.register(except_self=False, msg_types=consts.ATTACHMENT)(self.wechat_file_msg)
        self.bot.register(except_self=False, msg_types=consts.RECORDING)(self.wechat_voice_msg)
        self.bot.register(except_self=False, msg_types=consts.MAP)(self.wechat_location_msg)
        self.bot.register(except_self=False, msg_types=consts.VIDEO)(self.wechat_video_msg)
        self.bot.register(except_self=False, msg_types=consts.CARD)(self.wechat_card_msg)
        self.bot.register(except_self=False, msg_types=consts.FRIENDS)(self.wechat_friend_msg)
        self.bot.register(except_self=False, msg_types=consts.NOTE)(self.wechat_system_msg)

        @self.bot.register(msg_types=consts.SYSTEM)
        def wc_msg_system_log(msg):
            self.logger.debug("WeChat System Message:\n%s", repr(msg))

    @Decorators.wechat_msg_meta
    def wechat_text_msg(self, msg: wxpy.Message) -> EFBMsg:
        if msg.chat.user_name == "newsapp" and msg.text.startswith("<mmreader>"):
            return self.wechat_newsapp_msg(msg)
        if msg.text.startswith("http://weixin.qq.com/cgi-bin/redirectforward?args="):
            return self.wechat_location_msg(msg)
        efb_msg = EFBMsg()
        efb_msg.text = ews_utils.wechat_string_unescape(msg.text)
        efb_msg.type = MsgType.Text
        if msg.is_at:
            found = False
            for i in re.finditer("@([^@]*)(?=\u2005)", msg.text):
                if i.groups()[0] in (self.bot.self.name, msg.chat.self.display_name):
                    found = True
                    efb_msg.substitutions = EFBMsgSubstitutions({
                        i.span(): EFBChat(self.channel).self()
                    })
            if not found:
                append = "@" + self.bot.self.name
                efb_msg.substitutions = EFBMsgSubstitutions({
                    (len(msg.text) + 1, len(msg.text) + 1 + len(append)): EFBChat(self.channel).self()
                })
                efb_msg.text += " " + append
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_system_msg(self, msg: wxpy.Message) -> Optional[EFBMsg]:
        if msg.recalled_message_id:
            efb_msg = EFBMsg()
            efb_msg.chat = self.channel.chats.wxpy_chat_to_efb_chat(msg.chat)
            efb_msg.author = self.channel.chats.wxpy_chat_to_efb_chat(msg.sender)
            efb_msg.uid = str(msg.recalled_message_id)
            coordinator.send_status(EFBMessageRemoval(source_channel=self.channel,
                                                      destination_channel=coordinator.master,
                                                      message=efb_msg))
            return None
        efb_msg = EFBMsg()
        efb_msg.text = msg.text
        efb_msg.type = MsgType.Text
        efb_msg.author = EFBChat(self).system()
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_location_msg(self, msg: wxpy.Message) -> EFBMsg:
        efb_msg = EFBMsg()
        efb_msg.text = msg.text.split('\n')[0][:-1]
        # loc = re.search("=-?([0-9.]+),-?([0-9.]+)", msg.url).groups()
        # efb_msg.attributes = EFBMsgLocationAttribute(longitude=float(loc[1]), latitude=float(loc[0]))
        efb_msg.attributes = EFBMsgLocationAttribute(longitude=msg.location['x'], latitude=msg.location['y'])
        efb_msg.type = MsgType.Location
        return efb_msg

    def wechat_sharing_msg(self, msg: wxpy.Message) -> EFBMsg:
        self.logger.debug("[%s] Raw message: %s", msg.id, msg.raw)
        links = msg.articles
        if links is None:
            # If unsupported
            if msg.raw.get('Content', '') in self.UNSUPPORTED_MSG_PROMPT:
                return self.wechat_unsupported_msg(msg)
            else:
                try:
                    xml = xmltodict.parse(msg.raw.get('Content'))
                    type = xml.get('msg').get('appmsg').get('type')
                    source = xml.get('msg').get('appinfo').get('appname')
                    if type == 2:  # Image
                        return self.wechat_shared_image_msg(msg, source)
                    elif type in ('3', '5'):
                        title = xml.get('msg', {}).get('appmsg', {}).get('title', "")
                        des = xml.get('msg', {}).get('appmsg', {}).get('des', "")
                        url = xml.get('msg', {}).get('appmsg', {}).get('url', "")
                        return self.wechat_shared_link_msg(msg, source, title, des, url)
                    else:
                        # Unidentified message type
                        self.logger.error("[%s] Identified unsupported sharing message type. Raw message: %s",
                                          msg.id, msg.raw)
                        raise KeyError()
                except KeyError:
                    return self.wechat_unsupported_msg(msg)
        if self.channel.flag("first_link_only"):
            links = links[:1]
        for i in links:
            msg = self.wechat_raw_link_msg(msg, i.title, i.summary, i.cover, i.url)
        return msg

    @Decorators.wechat_msg_meta
    def wechat_unsupported_msg(self, msg: wxpy.Message) -> EFBMsg:
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.Unsupported
        efb_msg.text += "[消息类型不支持，请转到手机微信查看]"
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_shared_image_msg(self, msg: wxpy.Message, source: str, text: str = "", mode: str = "image") -> EFBMsg:
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.Image
        efb_msg.text = "来自" + source
        if text:
            efb_msg.text = "%s\n%s" % (text, efb_msg.text)
        efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg, app_message=mode)
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_shared_link_msg(self, msg: wxpy.Message, source: str, title: str, des: str, url: str) -> EFBMsg:
        share_mode = self.channel.flag('app_shared_link_mode')
        if share_mode == "image":
            # Share as image
            text = "%n\n%n\n%n" % (title, des, url)
            return self.wechat_shared_image_msg(msg, source, text=text, mode="thumbnail")
        else:
            image = None
            if share_mode == "upload":
                _, _, file = self.save_file(msg, app_message="thumbnail")
                r = requests.post("https://sm.ms/api/upload",
                                  files={"smfile": file},
                                  data={"ssl": True, "format": "json"}).json()
                if r.get('code', '') == 'success':
                    image = r['data']['url']
                    self.logger.log(99, "Delete link for Message \"%s\" [%s] is %s.",
                                    msg.id, title, r['data']['delete'])
                else:
                    self.logger.error("Failed to upload app link message as thumbnail to sm.ms: %s", r)
            elif share_mode != "ignore":
                self.logger.error('Not identified value for flag "app_shared_link_mode". Defaulted to ignore.')
            return self.wechat_raw_link_msg(msg, title, des, image, url)

    @Decorators.wechat_msg_meta
    def wechat_raw_link_msg(self, msg: wxpy.Message, title: str, description: str, image: str,
                            url: str, suffix: str="") -> EFBMsg:
        efb_msg = EFBMsg()
        if url:
            efb_msg.type = MsgType.Link
            efb_msg.text = suffix
            efb_msg.attributes = EFBMsgLinkAttribute(
                title=title,
                description=description,
                image=image,
                url=url
            )
        else:
            efb_msg.type = MsgType.Text
            efb_msg.text = "%s\n%s" % (title, description)
            if suffix:
                efb_msg.text += "\n%s" % suffix
            if image:
                efb_msg.text += "\n\n%s" % image
        return efb_msg

    def wechat_newsapp_msg(self, msg: wxpy.Message) -> EFBMsg:
        data = xmltodict.parse(msg.text)
        news = data.get('mmreader', {}).get('category', {}).get('newitem', [])
        if news:
            msg = self.wechat_raw_link_msg(msg, news[0]['title'], news[0]['digest'],
                                           news[0]['cover'], news[0]['shorturl'])
            if self.channel.flag("extra_links_on_message"):
                for i in news[1:]:
                    self.wechat_raw_link_msg(msg, i['title'], i['digest'], i['cover'], i['shorturl'])
        return msg

    @Decorators.wechat_msg_meta
    def wechat_picture_msg(self, msg: wxpy.Message) -> EFBMsg:
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.Image if msg.raw['MsgType'] == 3 else MsgType.Sticker
        try:
            if msg.raw['MsgType'] == 47 and not msg.raw['Content']:
                raise EOFError
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.text = ""
        except EOFError:
            efb_msg.type = MsgType.Unsupported
            efb_msg.text += "[图片无法接收，请转到手机微信查看]"
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_file_msg(self, msg: wxpy.Message) -> EFBMsg:
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.File
        try:
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.text = msg.file_name or ""
            efb_msg.filename = msg.file_name or ""
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += "[文件无法接收，请转到手机微信查看]"
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_voice_msg(self, msg: wxpy.Message) -> EFBMsg:
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.Audio
        try:
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.text = ""
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += "[语音无法接收，请转到手机微信查看]"
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_video_msg(self, msg: wxpy.Message) -> EFBMsg:
        efb_msg = EFBMsg()
        efb_msg.type = MsgType.Video
        try:
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.text = ""
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += "[视频无法接收，请转到手机微信查看]"
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_card_msg(self, msg: wxpy.Message) -> EFBMsg:
        efb_msg = EFBMsg()
        gender = {1: "男", 2: "女"}.get(msg.card.sex, msg.card.sex)
        txt = ("名片: {user.nick_name}\n"
               "来自: {user.province}, {user.city}\n"
               "签名: {user.signature}\n"
               "性别: {gender}")
        txt = txt.format(user=msg.card, gender=gender)
        efb_msg.text = txt
        efb_msg.type = MsgType.Text
        efb_msg.commands = EFBMsgCommands([
            EFBMsgCommand(
                name="发送好友请求",
                callable_name="add_friend",
                kwargs={"username": msg.card.user_name}
            )
        ])
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_friend_msg(self, msg: wxpy.Message) -> EFBMsg:
        efb_msg = EFBMsg()
        txt = ("Name card: {user.nick_name}\n"
               "From: {user.province}, {user.city}\n"
               "Signature: {user.signature}\n"
               "Gender: {user.sex}")
        txt = txt.format(user=msg.card)
        efb_msg.text = txt
        efb_msg.type = MsgType.Text
        efb_msg.commands = EFBMsgCommands([
            EFBMsgCommand(
                name="接受好友请求",
                callable_name="accept_friend",
                kwargs={"username": msg.card.user_name}
            )
        ])
        return efb_msg

    @staticmethod
    def save_file(msg: wxpy.Message, app_message: Optional[str]=None) -> Tuple[str, str, IO[bytes]]:
        """
        Args:
            msg: the WXPY message object
            app_message:
                Default: None
                * "image": Download from message as image
                * "thumbnail": Download from message as thumbnail
        Returns:
            File path, MIME, File
        """
        file = tempfile.NamedTemporaryFile()
        try:
            msg.get_file(file.name)
        except ValueError as e:
            # Non-standard file message
            if app_message in ('image', 'thumbnail'):
                url = '%s/webwxgetmsgimg' % msg.bot.core.loginInfo['url']
                params = {
                    'msgid': msg.id,
                    'skey': msg.bot.core.loginInfo['skey']
                }
                headers = {'User-Agent': itchat.config.USER_AGENT}
                if app_message == 'thumbnail':
                    params['type'] = 'slave'
                r = msg.bot.core.s.get(url, params=params, stream=True, headers=headers)
                for block in r.iter_content(1024):
                    file.write(block)
            else:
                raise e
        if os.fstat(file.fileno()).st_size <= 0:
            raise EOFError('File downloaded is Empty')
        file.seek(0)
        mime = magic.from_file(file.name, mime=True)
        if isinstance(mime, bytes):
            mime = mime.decode()
        return file.name, mime, file
