# coding: utf-8
from __future__ import unicode_literals

import atexit
import os
import pickle
import secrets
import logging
import logging.handlers

import threading
from typing import Optional, TYPE_CHECKING, Tuple
from collections import UserDict

if TYPE_CHECKING:
    from ..api.chats.chat import Chat

"""

# puid

尝试用聊天对象已知的属性，来查找对应的持久固定并且唯一的 用户 id


## 数据结构

PuidMap 中包含 4 个 dict，分别为

1. user_name -> puid
2. wxid -> puid
3. remark_name -> puid
4. caption (昵称, 性别, 省份, 城市) -> puid


## 查询逻辑

当给定一个 Chat 对象，需要获取对应的 puid 时，将按顺序，使用自己的对应属性，轮询以上 4 个 dict

* 若匹配任何一个，则获取到 puid，并将其他属性更新到其他的 dict
* 如果没有一个匹配，则创建一个新的 puid，并加入到以上的 4 个 dict


"""

# Type definitions
Caption = Tuple[str, Optional[str], Optional[str], Optional[str]]

file_io_logger: logging.Logger = logging.getLogger(__name__)


class PuidMap(object):

    SYSTEM_ACCOUNTS = {
        'filehelper': '文件传输助手',
        'newsapp': '腾讯新闻',
        'fmessage': '朋友推荐消息',
        'weibo': '微博账号 (weibo)',
        'qqmail': 'QQ邮箱 (qqmail)',
        'tmessage': '锑字消息 (tmessage)',
        'qmessage': '秋字消息 (qmessage)',
        'qqsync': 'QQ同步 (qqsync)',
        'floatbottle': '漂流瓶',
        'lbsapp': '位置分享 (lbsapp)',
        'shakeapp': '摇一摇',
        'medianote': '语音记事本',
        'qqfriend': 'QQ好友 (qqfriend)',
        'readerapp': '阅读应用 (readerapp)',
        'blogapp': '博客应用 (blogapp)',
        'facebookapp': 'Facebook',
        'masssendapp': '群发应用 (masssendapp)',
        'meishiapp': '美食应用 (meishiapp)',
        'feedsapp': '订阅应用 (feedsapp)',
        'voip': '网络通话 (voip)',
        'blogappweixin': '微信博客 (blogappweixin)',
        'weixin': '微信团队',
        'brandsessionholder': '品牌会话 (brandsessionholder)',
        'weixinreminder': '微信提醒 (weixinreminder)',
        'officialaccounts': '官方账号 (officialaccounts)',
        'notification_messages': '通知消息 (notification_messages)',
        'wxitil': '微习提尔 (wxitil)',
        'userexperience_alarm': '用户体验 (userexperience_alarm)'
    }

    DUMP_TIMEOUT = 30
    """Number of seconds before auto dump upon lookups."""

    logger: Optional[logging.Logger] = None

    def __init__(self, path, puid_logs=None):
        """
        用于获取聊天对象的 puid (持续有效，并且稳定唯一的用户ID)，和保存映射关系

        :param path: 映射数据的保存/载入路径
        :param puid_logs: PUID log path
        """
        self.path = path

        self.user_names = TwoWayDict()
        self.wxids = TwoWayDict()
        self.remark_names = TwoWayDict()

        self.captions = TwoWayDict()

        self._thread_lock = threading.Lock()

        if puid_logs:
            self.logger = logging.getLogger(__name__)
            try:
                self.logger.addHandler(logging.handlers.RotatingFileHandler(puid_logs))
            except IOError:
                self.logger = None
        else:
            self.logger = None

        if os.path.exists(self.path):
            self.load()

        self._dump_task: Optional[threading.Timer] = None

        atexit.register(self.dump)

    def log(self, *args, **kwargs):
        if self.logger:
            self.logger.debug(*args, **kwargs)

    @property
    def attr_dicts(self):
        return self.user_names, self.wxids, self.remark_names

    def __len__(self):
        return len(self.user_names)

    def __bool__(self):
        return bool(self.path)

    def __nonzero__(self):
        return bool(self.path)

    def get_puid(self, chat: 'Chat'):
        """
        获取指定聊天对象的 puid

        :param chat: 指定的聊天对象
        :return: puid
        :rtype: str
        """

        with self._thread_lock:
            self.log("Querying chat for PUID: %s", chat)

            if chat.user_name in PuidMap.SYSTEM_ACCOUNTS:
                self.log("%s is a recognised system chat.", chat.user_name)
                return chat.user_name

            if not (chat.user_name and chat.nick_name):
                self.log("%s has no user_name or nick_name.", chat)
                return

            # 3 of the stable attributes:
            # 1. Web WeChat temporary ID
            # 2. wxid (true permanent ID, almost unavailable)
            # 3. Remark name defined by user (Does this work?)
            chat_attrs = (
                chat.user_name,
                chat.wxid,
                getattr(chat, 'remark_name', None),
            )

            # 4 common attributes for matching:
            # 1. Chat base name
            # 2. Gender (for user)
            # 3. Province (for user)
            # 4. City (for user)
            chat_caption = self.get_caption(chat)

            puid = None

            self.log("Trying to match stable attributes: %s", chat_attrs)
            for i in range(3):
                puid = self.attr_dicts[i].get(chat_attrs[i])
                if puid:
                    self.log("Chat %s is matched to PUID %s with attribute %s", chat, puid, i)
                    break

            if not puid:
                self.log("Stable attribute failed, trying to match common attributes: %s", chat_caption)
                captions = self.captions
                for caption in captions:
                    if self.match_captions(caption, chat_caption):
                        puid = self.captions[caption]
                        self.log("Chat %s is matched to PUID %s attributes %s", chat, puid, caption)
                        break

            if puid:
                new_caption = self.merge_captions(self.captions.get_key(puid), chat_caption)
                value_updated = chat_caption != new_caption
                if value_updated:
                    self.log("Updating common attributes of %s from %s to %s", puid, chat_caption, new_caption)
            else:
                puid = chat.user_name[-8:]
                new_caption = self.get_caption(chat)
                self.log("Discovered new chat %s with common attributes %s. Assign new PUID: %s",
                         chat, new_caption, puid)
                value_updated = True

            for i in range(3):
                chat_attr = chat_attrs[i]
                if chat_attr:
                    old_attr = self.attr_dicts[i].get_key(puid)
                    if old_attr != chat_attr:
                        value_updated = True
                        self.log("Updating stable attributes #%s of PUID %s from %s to %s",
                                 i, puid, old_attr, chat_attr)
                    self.attr_dicts[i][chat_attr] = puid

            self.captions[new_caption] = puid

            if value_updated:
                self.activate_dump()
                self.log("Refreshing dump delay as value is changed.")

            return puid

    def activate_dump(self):
        """Activate dump timeout"""
        if self._dump_task:
            self._dump_task.cancel()

        self._dump_task = threading.Timer(self.DUMP_TIMEOUT, self.dump)
        self._dump_task.start()

    def dump(self):
        """
        保存映射数据
        """

        # Safe dump
        data = (self.user_names, self.wxids, self.remark_names, self.captions)
        if not os.path.exists(self.path):
            with open(self.path, "wb") as f:
                pickle.dump(data, f)
        else:
            file_io_logger.debug("Attempting to overwrite PUID mapping.")
            temp_path = f"{self.path}.{secrets.token_urlsafe(8)}"
            file_io_logger.debug(f"Write PUID mapping to {temp_path}.")
            with open(temp_path, "wb") as f:
                pickle.dump(data, f)
            file_io_logger.debug(f"Remove old PUID mapping at {self.path}")
            os.unlink(self.path)
            file_io_logger.debug(f"Move new PUID mapping from {temp_path} to {self.path}")
            os.rename(temp_path, self.path)
            file_io_logger.debug(f"PUID mapping overwrite completed.")

        if self._dump_task:
            self._dump_task = None

        self.log("Successfully dumped PUID map to: %s", self.path)
        self.log("Dumped - user_names: %s", self.user_names)
        self.log("Dumped - wxids: %s", self.wxids)
        self.log("Dumped - remark_names: %s", self.remark_names)
        self.log("Dumped - captions: %s", self.captions)

    def load(self, recur=False):
        """
        载入映射数据
        """
        self.log("Loading PUID map from local disk: %s", self.path)
        try:
            with open(self.path, 'rb') as fp:
                self.user_names, self.wxids, self.remark_names, self.captions = pickle.load(fp)
                self.log("Local disk - user_names: %s", self.user_names)
                self.log("Local disk - wxids: %s", self.wxids)
                self.log("Local disk - remark_names: %s", self.remark_names)
                self.log("Local disk - captions: %s", self.captions)
        except (ImportError, ModuleNotFoundError) as e:
            # Mitigate the pickling issue of migrating .wxpy to .vendor.wxpy
            if recur:
                raise e
            src = open(self.path, 'rb').read()
            src = src.replace(b'cefb_wechat_slave.wxpy.', b'cefb_wechat_slave.vendor.wxpy.')
            with open(self.path, 'wb') as f:
                f.write(src)
            return self.load(recur=True)

    @staticmethod
    def get_caption(chat: 'Chat') -> Caption:
        return (
            chat.nick_name,
            getattr(chat, 'sex', None),
            getattr(chat, 'province', None),
            getattr(chat, 'city', None),
        )

    def match_captions(self, old: Caption, new: Caption) -> bool:
        """Full match of a 4-value tuple only when both side has a value"""
        if new[0] and old:
            for i in range(4):
                if old[i] and new[i] and old[i] != new[i]:
                    if i > 0:
                        self.log("Potential common attribute match: %s -> %s", old, new)
                    return False
            return True
        return False

    @staticmethod
    def merge_captions(old: Optional[Caption], new: Caption) -> Caption:
        """Merge a 4-value tuple where new values replaces old values"""
        if not old:
            return new
        else:
            cap: Caption = (new[0] or old[0], new[1] or old[1], new[2] or old[2], new[3] or old[3])
            return cap


class TwoWayDict(UserDict):
    """
    可双向查询，且 key, value 均为唯一的 dict
    限制: key, value 均须为不可变对象，且不支持 .update() 方法
    """

    def __init__(self):
        super(TwoWayDict, self).__init__()
        self._reversed = dict()

    def get_key(self, value):
        """
        通过 value 查找 key
        """
        return self._reversed.get(value)

    def del_value(self, value):
        """
        删除 value 及对应的 key
        """
        del self[self._reversed[value]]

    def __setitem__(self, key, value):
        if self.get(key) != value:
            if key in self:
                self.del_value(self[key])
            if value in self._reversed:
                del self[self.get_key(value)]
            self._reversed[value] = key
            return super(TwoWayDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        del self._reversed[self[key]]
        return super(TwoWayDict, self).__delitem__(key)

    def update(*args, **kwargs):
        raise NotImplementedError
