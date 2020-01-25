# coding: utf-8

import logging
from typing import Optional, List, TYPE_CHECKING, Dict, Any, Tuple
from uuid import uuid4

from ehforwarderbot import Chat
from ehforwarderbot.chat import ChatNotificationState, GroupChat, PrivateChat, SelfChatMember, SystemChat
from ehforwarderbot.exceptions import EFBChatNotFound
from ehforwarderbot.types import ChatID
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

        self.MISSING_GROUP: GroupChat = GroupChat(
            channel=self.channel,
            uid=ChatID("__error_group__"),
            name=self._("Group Missing")
        )

        self.MISSING_CHAT: PrivateChat = PrivateChat(
            channel=self.channel,
            uid=ChatID("__error_chat__"),
            name=self._("Chat Missing")
        )

        self.efb_chat_objs: Dict[str, Chat] = {}
        # Cached Chat objects. Key: tuple(chat PUID, group PUID or None)

        # Load system chats
        self.system_chats: List[Chat] = []
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

    @staticmethod
    def get_name_alias(chat: wxpy.Chat) -> Tuple[str, Optional[str]]:
        chat_name = ews_utils.wechat_string_unescape(chat.nick_name)
        chat_alias = getattr(chat, 'display_name', None) or getattr(chat, 'remark_name', None)
        if chat_alias:
            chat_alias = ews_utils.wechat_string_unescape(chat_alias)
        # Remove alias if its same as chat name
        if chat_alias == chat_name:
            chat_alias = None
        return chat_name, chat_alias

    def wxpy_chat_to_efb_chat(self, chat: wxpy.Chat) -> Chat:
        # self.logger.debug("Converting WXPY chat %r, %sin recursive mode", chat, '' if recursive else 'not ')
        # self.logger.debug("WXPY chat with ID: %s, name: %s, alias: %s;", chat.puid, chat.nick_name, chat.alias)
        if chat is None:
            return self.MISSING_USER

        cache_key = chat.puid

        chat_name, chat_alias = self.get_name_alias(chat)

        cached_obj: Optional[Chat] = None
        if cache_key in self.efb_chat_objs:
            cached_obj = self.efb_chat_objs[cache_key]
            if chat_name == cached_obj.name and chat_alias == cached_obj.alias:
                return cached_obj

        # if chat name or alias changes, update cache
        efb_chat: Chat
        chat_id = ChatID(chat.puid or f"__invalid_{uuid4()}__")
        if cached_obj:
            efb_chat = cached_obj
            efb_chat.uid = chat_id
            efb_chat.name = chat_name
            efb_chat.alias = chat_alias
            efb_chat.vendor_specific = {'is_mp': isinstance(chat, wxpy.MP)}

            if isinstance(chat, wxpy.Group):
                # Update members if necessary
                remote_puids = {i.puid for i in chat.members}
                local_ids = {i.uid for i in efb_chat.members if not isinstance(i, SelfChatMember)}
                # Add missing members
                missing_puids = remote_puids - local_ids
                for member in chat.members:
                    if member.puid in missing_puids:
                        member_name, member_alias = self.get_name_alias(member)
                        efb_chat.add_member(name=member_name, alias=member_alias, uid=member.puid,
                                            vendor_specific={'is_mp': False})
        elif chat == chat.bot.self:
            efb_chat = PrivateChat(channel=self.channel, uid=chat_id, name=chat_name,
                                   alias=chat_alias, vendor_specific={'is_mp': True}, other_is_self=True)
        elif isinstance(chat, wxpy.Group):
            efb_chat = GroupChat(channel=self.channel, uid=chat_id, name=chat_name,
                                 alias=chat_alias, vendor_specific={'is_mp': False})
            for i in chat.members:
                if i.user_name == self.bot.self.user_name:
                    continue
                member_name, member_alias = self.get_name_alias(i)
                efb_chat.add_member(name=member_name, alias=member_alias, uid=i.puid, vendor_specific={'is_mp': False})
        elif isinstance(chat, wxpy.MP):
            efb_chat = PrivateChat(channel=self.channel, uid=chat_id, name=chat_name,
                                   alias=chat_alias, vendor_specific={'is_mp': True})
        elif isinstance(chat, wxpy.User):
            efb_chat = PrivateChat(channel=self.channel, uid=chat_id, name=chat_name,
                                   alias=chat_alias, vendor_specific={'is_mp': False})
        else:
            efb_chat = SystemChat(channel=self.channel, uid=chat_id, name=chat_name,
                                  alias=chat_alias, vendor_specific={'is_mp': False})

        efb_chat.vendor_specific.update(self.generate_vendor_specific(chat))
        if efb_chat.vendor_specific.get('is_muted', False):
            efb_chat.notification = ChatNotificationState.MENTIONS

        self.efb_chat_objs[cache_key] = efb_chat

        return efb_chat

    def get_chats(self) -> List[Chat]:
        l = self.system_chats.copy()
        for i in self.bot.chats(self.channel.flag('refresh_friends')):
            l.append(self.wxpy_chat_to_efb_chat(i))
        return l

    def search_chat(self, uid: str, refresh: bool = False) -> Chat:
        """Search chat by temporary UserName."""
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

    def search_member(self, uid: str, member_id: str, refresh: bool = False) -> Chat:
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
            'is_muted':
                raw.get('Statues', 0) == self.CHAT_ROOM_NOTIFY_CLOSE if is_room_contact
                else bool(contact_flag & self.CONTACT_FLAG_NOTIFY_CLOSE_CONTACT),
            # WTF is ``statues``?!!? Seriously, you have spelt “status” correctly in the message object,
            # why can’t you do it this time?
            'is_top': bool(contact_flag & self.CONTACT_FLAG_TOP_CONTACT),
            'has_photo_album': bool(raw.get('SnsFlag', 0)),
        }
