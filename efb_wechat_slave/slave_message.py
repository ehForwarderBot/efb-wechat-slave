# coding: utf-8

import json
import logging
import re
import tempfile
import threading
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional, Tuple, Dict, BinaryIO
from xml.etree import ElementTree as ETree
from xml.etree.ElementTree import Element

import magic
import requests
from PIL import Image

from ehforwarderbot import Message, MsgType, Chat, coordinator
from ehforwarderbot.chat import ChatMember, SystemChatMember
from ehforwarderbot.message import LocationAttribute, LinkAttribute, MessageCommands, MessageCommand, \
    Substitutions
from ehforwarderbot.status import MessageRemoval, ChatUpdates
from ehforwarderbot.types import MessageID
from . import constants
from . import utils as ews_utils
from .vendor import wxpy
from .vendor.wxpy.api import consts

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
        # noinspection PyProtectedMember
        self._ = self.channel._
        self.bot: wxpy.Bot = channel.bot
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.wechat_msg_register()
        self.file_download_mutex_lock = threading.Lock()
        # Message ID: [JSON ID, remaining count]
        self.recall_msg_id_conversion: Dict[str, Tuple[str, int]] = dict()

    def get_chat_and_author(self, msg: wxpy.Message) -> Tuple[Chat, ChatMember]:
        chat = self.channel.chats.wxpy_chat_to_efb_chat(msg.chat)
        author: ChatMember
        if msg.author.user_name == self.bot.self.user_name and chat.self:
            author = chat.self
        else:
            try:
                author = chat.get_member(msg.author.puid)
            except KeyError:
                # Enrol the new member to cache on the spot.
                name, alias = self.channel.chats.get_name_alias(msg.author)
                author = chat.add_member(uid=msg.author.puid, name=name, alias=alias, vendor_specific={'is_mp': False})
        return chat, author

    class Decorators:
        @classmethod
        def wechat_msg_meta(cls, func: Callable):
            def wrap_func(self: 'SlaveMessageManager', msg: wxpy.Message, *args, **kwargs):
                logger = logging.getLogger(__name__)
                logger.debug("[%s] Raw message: %r", msg.id, msg.raw)

                efb_msg: Optional[Message] = func(self, msg, *args, **kwargs)

                if efb_msg is None:
                    return

                if getattr(coordinator, 'master', None) is None:
                    logger.debug("[%s] Dropping message as master channel is not ready yet.", efb_msg.uid)
                    return

                efb_msg.deliver_to = coordinator.master

                # Format message IDs as JSON of List[List[str]].
                efb_msg.uid = MessageID(json.dumps(
                    [[str(getattr(msg, "id", constants.INVALID_MESSAGE_ID + str(uuid.uuid4())))]]
                ))

                if not efb_msg.chat or not efb_msg.author:
                    chat, author = self.get_chat_and_author(msg)

                    # Do not override what's defined in the wrapped methods
                    efb_msg.chat = efb_msg.chat or chat
                    efb_msg.author = efb_msg.author or author

                logger.debug("[%s] Chat: %s, Author: %s", efb_msg.uid, efb_msg.chat, efb_msg.author)

                coordinator.send_message(efb_msg)
                if efb_msg.file:
                    efb_msg.file.close()

            def thread_wrapper(*args, **kwargs):
                """Run message requests in separate threads to prevent blocking"""
                threading.Thread(target=wrap_func, args=args, kwargs=kwargs,
                                 name=f"EWS slave message thread running {func}").run()

            return thread_wrapper

    def wechat_msg_register(self):
        self.bot.register(except_self=False, msg_types=consts.TEXT)(self.wechat_text_msg)
        self.bot.register(except_self=False, msg_types=consts.SHARING)(self.wechat_sharing_msg)
        self.bot.register(except_self=False, msg_types=consts.PICTURE)(self.wechat_picture_msg)
        self.bot.register(except_self=False, msg_types=consts.STICKER)(self.wechat_sticker_msg)
        self.bot.register(except_self=False, msg_types=consts.ATTACHMENT)(self.wechat_file_msg)
        self.bot.register(except_self=False, msg_types=consts.RECORDING)(self.wechat_voice_msg)
        self.bot.register(except_self=False, msg_types=consts.MAP)(self.wechat_location_msg)
        self.bot.register(except_self=False, msg_types=consts.VIDEO)(self.wechat_video_msg)
        self.bot.register(except_self=False, msg_types=consts.CARD)(self.wechat_card_msg)
        self.bot.register(except_self=False, msg_types=consts.FRIENDS)(self.wechat_friend_msg)
        self.bot.register(except_self=False, msg_types=consts.NOTE)(self.wechat_system_msg)
        self.bot.register(except_self=False, msg_types=consts.UNSUPPORTED)(self.wechat_system_unsupported_msg)

        @self.bot.register(msg_types=consts.SYSTEM)
        def wc_msg_system_log(msg):
            self.logger.debug("WeChat System Message:\n%s", repr(msg))

    @Decorators.wechat_msg_meta
    def wechat_text_msg(self, msg: wxpy.Message) -> Optional[Message]:
        if msg.chat.user_name == "newsapp" and msg.text.startswith("<mmreader>"):
            return self.wechat_newsapp_msg(msg)
        if msg.text.startswith("http://weixin.qq.com/cgi-bin/redirectforward?args="):
            return self.wechat_location_msg(msg)
        chat, author = self.get_chat_and_author(msg)
        if self.channel.flag("text_post_processing"):
            text = ews_utils.wechat_string_unescape(msg.text)
        else:
            text = msg.text or ""
        efb_msg = Message(
            chat=chat, author=author,
            text=text,
            type=MsgType.Text
        )
        if msg.is_at and chat.self:
            found = False
            for i in re.finditer(r"@([^@\s]*)(?=\u2005|$|\s)", msg.text):
                if i.groups()[0] in (self.bot.self.name, msg.chat.self.display_name):
                    found = True
                    efb_msg.substitutions = Substitutions({
                        i.span(): chat.self
                    })
            if not found:
                append = "@" + self.bot.self.name
                efb_msg.substitutions = Substitutions({
                    (len(msg.text) + 1, len(msg.text) + 1 + len(append)): chat.self
                })
                efb_msg.text += " " + append
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_system_unsupported_msg(self, msg: wxpy.Message) -> Optional[Message]:
        if msg.raw['MsgType'] in (50, 52, 53):
            text = self._("[Incoming audio/video call, please check your phone.]")
        else:
            return None
        efb_msg = Message(
            text=text,
            type=MsgType.Unsupported,
        )
        return efb_msg

    NEW_CHAT_PATTERNS = {
        "invited you to a group", "グループチャットに参加しました",
        "现在可以开始聊天了。", "Start chatting!", "チャットを始めましょう!"
        "You've joined this group chat.",
        "邀请你加入了群聊", "邀请你和", "invited you and",
        "invited you to a group chat with"
    }
    CHAT_UPDATE_PATTERNS = {
        "修改群名为", "changed the group name to"
    }
    NEW_CHAT_MEMBER_PATTERNS = {
        "グループチャットに招待しました", "to the group chat"
    }
    CHAT_MEMBER_UPDATE_PATTERNS = {
        "グループマネージャーになりました",
    }
    REMOVE_CHAT_MEMBER_PATTERNS = {
        "移出了群聊"
    }
    CHAT_AND_MEMBER_UPDATE_PATTERNS = (
            CHAT_UPDATE_PATTERNS | NEW_CHAT_MEMBER_PATTERNS |
            CHAT_MEMBER_UPDATE_PATTERNS | REMOVE_CHAT_MEMBER_PATTERNS
    )

    @Decorators.wechat_msg_meta
    def wechat_system_msg(self, msg: wxpy.Message) -> Optional[Message]:
        if msg.recalled_message_id:
            recall_id = str(msg.recalled_message_id)
            # check conversion table first
            if recall_id in self.recall_msg_id_conversion:
                # prevent feedback of messages deleted by master channel.
                del self.recall_msg_id_conversion[recall_id]
                return None
                # val = self.recall_msg_id_conversion.pop(recall_id)
                # val[1] -= 1
                # if val[1] > 0:  # not all associated messages are recalled.
                #     return None
                # else:
                #     efb_msg.uid = val[0]
            else:
                # Format message IDs as JSON of List[List[str]].
                chat, author = self.get_chat_and_author(msg)
                efb_msg = Message(
                    chat=chat, author=author,
                    uid=MessageID(json.dumps([[recall_id]]))
                )
            coordinator.send_status(MessageRemoval(source_channel=self.channel,
                                                   destination_channel=coordinator.master,
                                                   message=efb_msg))
            return None
        chat, _ = self.get_chat_and_author(msg)
        try:
            author = chat.get_member(SystemChatMember.SYSTEM_ID)
        except KeyError:
            author = chat.add_system_member()
        if any(i in msg.text for i in self.NEW_CHAT_PATTERNS):
            coordinator.send_status(ChatUpdates(
                channel=self.channel,
                new_chats=(chat.uid,)
            ))
        elif any(i in msg.text for i in self.CHAT_AND_MEMBER_UPDATE_PATTERNS):
            # TODO: detect actual member changes from message text
            coordinator.send_status(ChatUpdates(
                channel=self.channel,
                modified_chats=(chat.uid,)
            ))
        return Message(
            text=msg.text,
            type=MsgType.Text,
            chat=chat,
            author=author,
        )

    @Decorators.wechat_msg_meta
    def wechat_location_msg(self, msg: wxpy.Message) -> Message:
        efb_msg = Message()
        efb_msg.text = msg.text.split('\n')[0][:-1]
        efb_msg.attributes = LocationAttribute(latitude=float(msg.location['x']),
                                               longitude=float(msg.location['y']))
        efb_msg.type = MsgType.Location
        return efb_msg

    def wechat_sharing_msg(self, msg: wxpy.Message):
        # This method is not wrapped by wechat_msg_meta decorator, thus no need to return Message object.
        self.logger.debug("[%s] Raw message: %s", msg.id, msg.raw)
        links = msg.articles
        if links is None:
            # If unsupported
            if msg.raw.get('Content', '') in self.UNSUPPORTED_MSG_PROMPT:
                return self.wechat_unsupported_msg(msg)
            else:
                try:
                    xml = ETree.fromstring(msg.raw.get('Content'))
                    appmsg_type = self.get_node_text(xml, './appmsg/type', "")
                    source = self.get_node_text(xml, './appinfo/appname', "")
                    if appmsg_type == '2':  # Image
                        return self.wechat_shared_image_msg(msg, source)
                    elif appmsg_type in ('3', '4', '5'):
                        title = self.get_node_text(xml, './appmsg/title', "")
                        des = self.get_node_text(xml, './appmsg/des', "")
                        url = self.get_node_text(xml, './appmsg/url', "")
                        return self.wechat_shared_link_msg(msg, source, title, des, url)
                    elif appmsg_type in ('33', '36'):  # Mini programs (wxapp)
                        title = self.get_node_text(xml, './appmsg/sourcedisplayname', "") or \
                                self.get_node_text(xml, './appmsg/appinfo/appname', "") or \
                                self.get_node_text(xml, './appmsg/title', "")
                        des = self.get_node_text(xml, './appmsg/title', "")
                        url = self.get_node_text(xml, './appmsg/url', "")
                        return self.wechat_shared_link_msg(msg, source, title, des, url)
                    elif appmsg_type == '1':  # Strange “app message” that looks like a text link
                        msg.raw['text'] = self.get_node_text(xml, './appmsg/title', "")
                        return self.wechat_text_msg(msg)
                    else:
                        # Unidentified message type
                        self.logger.error("[%s] Identified unsupported sharing message type. Raw message: %s",
                                          msg.id, msg.raw)
                        raise KeyError()
                except (TypeError, KeyError, ValueError, ETree.ParseError):
                    return self.wechat_unsupported_msg(msg)
        if self.channel.flag("first_link_only"):
            links = links[:1]

        for i in links:
            self.wechat_raw_link_msg(msg, i.title, i.summary, i.cover, i.url)

    @Decorators.wechat_msg_meta
    def wechat_unsupported_msg(self, msg: wxpy.Message) -> Message:
        efb_msg = Message()
        efb_msg.type = MsgType.Unsupported
        efb_msg.text += self._("[Unsupported message, please check your phone.]")
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_shared_image_msg(self, msg: wxpy.Message, source: str, text: str = "", mode: str = "image") -> Message:
        efb_msg = Message()
        efb_msg.type = MsgType.Image
        efb_msg.text = self._("Via {source}").format(source=source)
        if text:
            efb_msg.text = "%s\n%s" % (text, efb_msg.text)
        efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg, app_message=mode)
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_shared_link_msg(self, msg: wxpy.Message, source: str, title: str, des: str, url: str) -> Message:
        share_mode = self.channel.flag('app_shared_link_mode')
        xml = ETree.fromstring(msg.raw.get('Content'))
        thumb_url = self.get_node_text(xml, ".//thumburl", "")
        via = self._("Via {source}").format(source=source) if source else ""
        if thumb_url:
            return self.wechat_raw_link_msg(msg, title, des, thumb_url, url)
        if share_mode == "image":
            # Share as image
            text = f"{title}\n{des}\n{url}"
            return self.wechat_shared_image_msg(msg, source, text=text, mode="thumbnail")
        else:
            image = None
            if share_mode == "upload":
                try:
                    _, _, file = self.save_file(msg, app_message="thumbnail")
                    r = requests.post("https://sm.ms/api/v2/upload",
                                      files={"smfile": file},
                                      headers={"Authorization": "14ac5499cfdd2bb2859e4476d2e5b1d2bad079bf"},
                                      data={"format": "json"}).json()
                    if r.get('code', '') == 'success':
                        image = r['data']['url']
                        self.logger.info("Delete link for picture of message \"%s\" [%s] is %s.",
                                         msg.id, title, r['data']['delete'])
                    else:
                        self.logger.error("Failed to upload app link message as thumbnail to sm.ms: %s", r)
                except EOFError as e:
                    self.logger.error("Failed to download app link message thumbnail: %r", e)
            elif share_mode != "ignore":
                self.logger.error('Not identified value for flag "app_shared_link_mode". Defaulted to ignore.')
            return self.wechat_raw_link_msg(msg, title, des, image, url, suffix=via)

    @Decorators.wechat_msg_meta
    def wechat_raw_link_msg(self, msg: wxpy.Message, title: str, description: str, image: str,
                            url: str, suffix: str = "") -> Message:

        if url:
            efb_msg = Message(
                type=MsgType.Link,
                text=suffix,
                attributes=LinkAttribute(
                    title=title,
                    description=description,
                    image=image,
                    url=url
                )
            )
        else:
            efb_msg = Message(
                type=MsgType.Text,
                text=f"{title}\n{description}",
            )
            if suffix:
                efb_msg.text += f"\n{suffix}"
            if image:
                efb_msg.text += f"\n\n{image}"
        return efb_msg

    def wechat_newsapp_msg(self, msg: wxpy.Message) -> Optional[Message]:
        xml = ETree.fromstring(msg.raw.get('Content'))
        news = xml.findall('.//category/item')
        e_msg = None
        if news:
            e_msg = self.wechat_raw_link_msg(msg,
                                             self.get_node_text(news[0], 'title', ""),
                                             self.get_node_text(news[0], 'digest', ""),
                                             self.get_node_text(news[0], 'cover', ""),
                                             self.get_node_text(news[0], 'shorturl', ""))
            for i in news[1:]:
                self.wechat_raw_link_msg(msg,
                                         self.get_node_text(i, 'title', ""),
                                         self.get_node_text(i, 'digest', ""),
                                         self.get_node_text(i, 'cover', ""),
                                         self.get_node_text(i, 'shorturl', ""))
        return e_msg

    @Decorators.wechat_msg_meta
    def wechat_picture_msg(self, msg: wxpy.Message) -> Message:
        efb_msg = Message(type=MsgType.Image)
        try:
            if msg.raw['MsgType'] == 47 and not msg.raw['Content']:
                raise EOFError
            if msg.file_size == 0:
                raise EOFError
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.filename = msg.file_name
            # ^ Also throws EOFError
            efb_msg.text = ""
        except EOFError:
            efb_msg.text += self._("[Failed to download the picture, please check your phone.]")
            efb_msg.type = MsgType.Unsupported

        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_sticker_msg(self, msg: wxpy.Message) -> Message:
        efb_msg = Message(type=MsgType.Sticker)
        try:
            if msg.raw['MsgType'] == 47 and not msg.raw['Content']:
                raise EOFError
            if msg.file_size == 0:
                raise EOFError
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.filename = msg.file_name
            # ^ Also throws EOFError
            if 'gif' in efb_msg.mime and Image.open(efb_msg.path).is_animated:
                efb_msg.type = MsgType.Animation
            efb_msg.text = ""
        except EOFError:
            efb_msg.text += self._("[Failed to download the sticker, please check your phone.]")
            efb_msg.type = MsgType.Unsupported

        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_file_msg(self, msg: wxpy.Message) -> Message:
        efb_msg = Message(type=MsgType.File)
        try:
            file_name = msg.file_name
            efb_msg.text = file_name or ""
            app_name = msg.app_name
            if app_name:
                efb_msg.text = self._("{file_name} sent via {app_name}").format(file_name=file_name, app_name=app_name)
            efb_msg.filename = file_name or ""
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += self._("[Failed to download the file, please check your phone.]")
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_voice_msg(self, msg: wxpy.Message) -> Message:
        efb_msg = Message(type=MsgType.Voice)
        try:
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.text = ""
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += self._("[Failed to download the voice message, please check your phone.]")
        return efb_msg

    @Decorators.wechat_msg_meta
    def wechat_video_msg(self, msg: wxpy.Message) -> Message:
        efb_msg = Message(type=MsgType.Video)
        try:
            if msg.file_size == 0:
                raise EOFError
            efb_msg.path, efb_msg.mime, efb_msg.file = self.save_file(msg)
            efb_msg.filename = msg.file_name
            efb_msg.text = ""
        except EOFError:
            efb_msg.type = MsgType.Text
            efb_msg.text += self._("[Failed to download the video message, please check your phone.]")
        return efb_msg

    def generate_card_info(self, msg: wxpy.Message) -> str:
        gender = {1: self._("M"), 2: self._("F")}.get(msg.card.sex, msg.card.sex)
        txt = (self._("Card: {user.nick_name}\n"
                      "From: {user.province}, {user.city}\n"
                      "Bio: {user.signature}\n"
                      "Gender: {gender}"))
        txt = txt.format(user=msg.card, gender=gender)
        return txt

    @Decorators.wechat_msg_meta
    def wechat_card_msg(self, msg: wxpy.Message) -> Message:
        # TRANSLATORS: Gender of contact
        txt = self.generate_card_info(msg)
        return Message(
            text=txt,
            type=MsgType.Text,
            commands=MessageCommands([
                MessageCommand(
                    name=self._("Send friend request"),
                    callable_name="add_friend",
                    kwargs={"username": msg.card.user_name}
                )
            ])
        )

    @Decorators.wechat_msg_meta
    def wechat_friend_msg(self, msg: wxpy.Message) -> Message:
        # TRANSLATORS: Gender of contact
        txt = self.generate_card_info(msg)
        return Message(
            text=txt,
            type=MsgType.Text,
            commands=MessageCommands([
                MessageCommand(
                    name=self._("Accept friend request"),
                    callable_name="accept_friend",
                    kwargs={"username": msg.card.user_name}
                )
            ])
        )

    def save_file(self, msg: wxpy.Message, app_message: Optional[str] = None) -> Tuple[Path, str, BinaryIO]:
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
        file: BinaryIO = tempfile.NamedTemporaryFile()  # type: ignore
        try:
            if msg.type in [consts.ATTACHMENT, consts.VIDEO]:
                with self.file_download_mutex_lock:
                    msg.get_file(file.name)
            else:
                msg.get_file(file.name)
        except ValueError as e:
            # Non-standard file message
            if app_message in ('image', 'thumbnail'):
                url = '%s/webwxgetmsgimg' % msg.bot.core.loginInfo['url']
                params = {
                    'msgid': msg.id,
                    'skey': msg.bot.core.loginInfo['skey']
                }
                headers = {'User-Agent': self.bot.user_agent}
                if app_message == 'thumbnail':
                    params['type'] = 'slave'
                r = msg.bot.core.s.get(url, params=params, stream=True, headers=headers)
                for block in r.iter_content(1024):
                    file.write(block)
            else:
                raise e
        if file.seek(0, 2) <= 0:
            raise EOFError('File downloaded is Empty')
        else:
            self.logger.debug("[%s] File size: %s", msg.id, file.seek(0, 2))
        file.seek(0)
        mime = magic.from_file(file.name, mime=True)
        if isinstance(mime, bytes):
            mime = mime.decode()
        self.logger.debug("[%s] File downloaded: %s (%s)", msg.id, file.name, mime)
        return Path(file.name), mime, file

    @staticmethod
    def get_node_text(root: Element, path: str, fallback: str) -> str:
        node = root.find(path)
        return getattr(node, 'text', fallback) or fallback
