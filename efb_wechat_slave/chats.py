# coding: utf-8

import logging
from typing import Optional, List, TYPE_CHECKING, Dict, Any, Tuple

from ehforwarderbot import EFBChat
from ehforwarderbot.chat import EFBChatNotificationState
from ehforwarderbot.constants import ChatType
from ehforwarderbot.exceptions import EFBChatNotFound
from . import utils as ews_utils
from .vendor import wxpy

if TYPE_CHECKING:
    from . import WeChatChannel


class ChatManager:

    def __init__(self, channel: 'WeChatChannel'):
        self.channel: 'WeChatChannel' = channel
        self.logger: logging.Logger = logging.getLogger(__name__)

        # noinspection PyProtectedMember
        self._ = self.channel._

        self.MISSING_GROUP: EFBChat = EFBChat(self.channel)
        self.MISSING_GROUP.chat_uid = "__error__"
        self.MISSING_GROUP.chat_type = ChatType.Group
        self.MISSING_GROUP.chat_name = self._("Chat Missing")
        self.MISSING_GROUP.chat_alias = None

        self.MISSING_USER: EFBChat = EFBChat(self.channel)
        self.MISSING_USER.chat_uid = "__error__"
        self.MISSING_USER.chat_type = ChatType.User
        self.MISSING_USER.chat_name = self._("Chat Missing")
        self.MISSING_USER.chat_alias = None

        self.efb_chat_objs: Dict[Tuple[str, Optional[str]], EFBChat] = {}
        # Cached EFBChat objects. Key: tuple(chat PUID, group PUID or None)

        # Load system chats
        self.system_chats: List[EFBChat] = []
        for i in channel.flag('system_chats_to_include'):
            self.system_chats.append(
                self.wxpy_chat_to_efb_chat(
                    wxpy.Chat(
                        wxpy.utils.wrap_user_name(i),
                        self.bot
                    )
                )
            )

    @property
    def bot(self):
        return self.channel.bot

    def get_chat_by_puid(self, puid: str) -> EFBChat:
        if puid in wxpy.Chat.SYSTEM_ACCOUNTS:
            efb_chat = self.wxpy_chat_to_efb_chat(wxpy.Chat(wxpy.utils.wrap_user_name(puid), self.bot))
            assert efb_chat is not None
            efb_chat.chat_type = ChatType.System
            return efb_chat
        try:
            chat: wxpy.Chat = wxpy.ensure_one(self.bot.search(puid=puid))
            return self.wxpy_chat_to_efb_chat(chat)
        except ValueError:
            try:
                self.bot.chats(update=True)
                chat = wxpy.ensure_one(self.bot.search(puid=puid))
                return self.wxpy_chat_to_efb_chat(chat)
            except ValueError:
                return self.MISSING_USER

    def get_wxpy_chat_by_uid(self, uid: str) -> wxpy.Chat:
        if uid in wxpy.Chat.SYSTEM_ACCOUNTS:
            return wxpy.Chat(wxpy.utils.wrap_user_name(uid), self.bot)
        try:
            return wxpy.ensure_one(self.bot.search(puid=uid))
        except ValueError:
            try:
                self.bot.chats(update=True)
                chat: wxpy.Chat = wxpy.ensure_one(self.bot.search(puid=uid))
                return chat
            except ValueError:
                return wxpy.Chat(wxpy.utils.wrap_user_name(uid), self.bot)

    def wxpy_chat_to_efb_chat(self, chat: wxpy.Chat, recursive=True) -> EFBChat:
        # self.logger.debug("Converting WXPY chat %r, %sin recursive mode", chat, '' if recursive else 'not ')
        # self.logger.debug("WXPY chat with ID: %s, name: %s, alias: %s;", chat.puid, chat.nick_name, chat.alias)
        if chat is None:
            return self.MISSING_USER

        # Use chat puid and group puid as key, update cache if name is changed.
        if isinstance(chat, wxpy.Member):
            # noinspection PyBroadException
            try:
                cache_key = (chat.puid, chat.group.puid)
            except Exception:
                # [Note] chat.group might not be available, and raises `Exception`.
                # Need to deal with this option.
                cache_key = (chat.puid, None)
        else:
            cache_key = (chat.puid, None)

        # if chat name or alias changes, update cache immediately
        chat_name = ews_utils.wechat_string_unescape(chat.nick_name)
        chat_alias = getattr(chat, 'display_name', None) or getattr(chat, 'remark_name', None)
        cached_obj: EFBChat = None
        if chat_alias:
            chat_alias = ews_utils.wechat_string_unescape(chat_alias)
        if cache_key in self.efb_chat_objs:
            cached_obj = self.efb_chat_objs[cache_key]
            if chat_name == cached_obj.chat_name and chat_alias == cached_obj.chat_alias:
                return cached_obj
        efb_chat: EFBChat = cached_obj or EFBChat(self.channel)
        efb_chat.chat_uid = chat.puid or "__invalid__"
        efb_chat.chat_name = chat_name
        efb_chat.chat_alias = chat_alias
        efb_chat.chat_type = ChatType.System
        efb_chat.vendor_specific = {'is_mp': False}
        if isinstance(chat, wxpy.Member):
            efb_chat.chat_type = ChatType.User
            efb_chat.is_chat = False
            if recursive:
                efb_chat.group = self.wxpy_chat_to_efb_chat(chat.group, False)
        elif isinstance(chat, wxpy.Group):
            efb_chat.chat_type = ChatType.Group
            for i in chat.members:
                efb_chat.members.append(self.wxpy_chat_to_efb_chat(i, False))
                efb_chat.members[-1].group = efb_chat
        elif isinstance(chat, wxpy.MP):
            efb_chat.chat_type = ChatType.User
            efb_chat.vendor_specific['is_mp'] = True
        elif isinstance(chat, wxpy.User):
            efb_chat.chat_type = ChatType.User
        if chat == chat.bot.self:
            efb_chat.self()

        efb_chat.vendor_specific.update(self.generate_vendor_specific(chat))
        if efb_chat.vendor_specific.get('is_muted', False):
            efb_chat.notification = EFBChatNotificationState.MENTIONS

        self.efb_chat_objs[cache_key] = efb_chat

        return efb_chat

    def get_chats(self) -> List[EFBChat]:
        l = self.system_chats.copy()
        for i in self.bot.chats(self.channel.flag('refresh_friends')):
            l.append(self.wxpy_chat_to_efb_chat(i))
        return l

    def search_chat(self, uid: str, refresh: bool = False) -> EFBChat:
        try:
            if refresh:
                self.bot.chats(True)
            if uid in wxpy.Chat.SYSTEM_ACCOUNTS:
                chat: wxpy.Chat = wxpy.Chat(wxpy.utils.wrap_user_name(uid), self.bot)
            else:
                chat = wxpy.utils.ensure_one(self.bot.search(puid=uid))
            return self.wxpy_chat_to_efb_chat(chat)
        except ValueError:
            if not refresh:
                return self.search_chat(uid, refresh=True)
            else:
                raise EFBChatNotFound()

    def search_member(self, uid: str, member_id: str, refresh: bool = False) -> EFBChat:
        group = self.search_chat(uid)
        if not isinstance(group, wxpy.Group):
            raise EFBChatNotFound()
        try:
            if refresh:
                self.bot.chats(True)
            chat: wxpy.Chat = wxpy.utils.ensure_one(group.search(puid=member_id))
            return self.wxpy_chat_to_efb_chat(chat)
        except ValueError:
            if not refresh:
                return self.search_chat(uid, refresh=True)
            else:
                raise EFBChatNotFound()

    # Constants extracted from Web WC source, see EWS#27.
    CONTACT_FLAG_CONTACT = 1
    CONTACT_FLAG_CHAT_CONTACT = 2
    CONTACT_FLAG_CHAT_ROOM_CONTACT = 4
    CONTACT_FLAG_BLACKLIST_CONTACT = 8
    # CONTACT_FLAG_DOMAIN_CONTACT = 16
    # CONTACT_FLAG_HIDE_CONTACT = 32
    # CONTACT_FLAG_FAVOUR_CONTACT = 64
    # CONTACT_FLAG_3RD_APP_CONTACT = 128
    # CONTACT_FLAG_SNS_BLACKLIST_CONTACT = 256
    CONTACT_FLAG_NOTIFY_CLOSE_CONTACT = 512
    CONTACT_FLAG_TOP_CONTACT = 2048
    # MM_USER_ATTR_VERIFY_FLAG_BIZ = 1
    # MM_USER_ATTR_VERIFY_FLAG_FAMOUS = 2
    # MM_USER_ATTR_VERIFY_FLAG_BIZ_BIG = 4
    MM_USER_ATTR_VERIFY_FLAG_BIZ_BRAND = 8
    # MM_USER_ATTR_VERIFY_FLAG_BIZ_VERIFIED = 16
    CHAT_ROOM_NOTIFY_CLOSE = 0

    def generate_vendor_specific(self, chat: wxpy.Chat) -> Dict[str, Any]:
        """
        Generate a set of vendor specific attributes from chat.
        Features extracted from Web WC source, see EWS#27.
        """
        is_self = chat == chat.bot.self
        raw = chat.raw
        is_room_contact = isinstance(chat, wxpy.Group)
        username = raw.get('UserName', '')
        contact_flag = raw.get('ContactFlag', 0)
        return {
            'is_contact': bool(contact_flag & self.CONTACT_FLAG_CONTACT) or is_self,
            'is_blacklist_contact': bool(contact_flag & self.CONTACT_FLAG_BLACKLIST_CONTACT),
            'is_conversation_contact': bool(contact_flag & self.CONTACT_FLAG_CHAT_CONTACT),
            'is_room_contact_del': is_room_contact and not bool(contact_flag & self.CONTACT_FLAG_CHAT_ROOM_CONTACT),
            'is_room_owner': is_room_contact and bool(raw.get('isOwner', 0)),
            'is_brand_contact': bool(raw.get('VerifyFlag', 0) & self.MM_USER_ATTR_VERIFY_FLAG_BIZ_BRAND),
            'is_sp_contact': '@' not in username or username.endswith("@qqim"),
            'is_shield_user': username.endswith("@lbsroom") or username.endswith('@talkroom'),
            'is_muted': raw.get('Status', 0) == self.CHAT_ROOM_NOTIFY_CLOSE if is_room_contact
            else bool(contact_flag & self.CONTACT_FLAG_NOTIFY_CLOSE_CONTACT),
            'is_top': bool(contact_flag & self.CONTACT_FLAG_TOP_CONTACT),
            'has_photo_album': bool(raw.get('SnsFlag', 0)),
        }
