import base64
import io
import logging
import mimetypes
import os
import tempfile
import threading
from tempfile import NamedTemporaryFile
from typing import IO, Any, Dict, Optional, List

import time
import yaml
from PIL import Image
from pyqrcode import QRCode

from ehforwarderbot import EFBChannel, EFBMsg, MsgType, ChannelType, \
    ChatType, EFBStatus, EFBChat, coordinator
from ehforwarderbot import utils as efb_utils
from ehforwarderbot.exceptions import EFBMessageTypeNotSupported, EFBMessageError, EFBChatNotFound, \
    EFBOperationNotSupported
from ehforwarderbot.message import EFBMsgCommands, EFBMsgCommand
from ehforwarderbot.utils import extra
from ehforwarderbot.status import EFBMessageRemoval
from . import wxpy
from . import __version__ as version
from .utils import ExperimentalFlagsManager
from . import utils as ews_utils
from .chats import ChatManager
from .slave_message import SlaveMessageManager


class WeChatChannel(EFBChannel):
    """
    EFB Channel - WeChat Slave Channel
    Based on wxpy (itchat), WeChat Web Client

    Author: Eana Hufwe <https://github.com/blueset>
    """

    channel_name = "WeChat Slave"
    channel_emoji = "💬"
    channel_id = 'blueset.wechat'
    channel_type = ChannelType.Slave

    __version__ = version.__version__

    supported_message_types = {MsgType.Text, MsgType.Sticker, MsgType.Image,
                               MsgType.File, MsgType.Video, MsgType.Link, MsgType.Audio}
    logger: logging.Logger = logging.getLogger("plugins.%s.WeChatChannel" % channel_id)
    qr_uuid: str = ""
    done_reauth: threading.Event = threading.Event()
    _stop_polling_event: threading.Event = threading.Event()

    config = dict()

    # Constants
    MAX_FILE_SIZE: int = 5 * 2 ** 20

    def __init__(self):
        """
        Initialize the channel
        
        Args:
            coordinator (:obj:`ehforwarderbot.coordinator.EFBCoordinator`):
                The EFB framework coordinator
        """
        super().__init__()
        self.load_config()

        self.flag: ExperimentalFlagsManager = ExperimentalFlagsManager(self)

        self.authenticate('console_qr_code')

        # Managers
        self.slave_message: SlaveMessageManager = SlaveMessageManager(self)
        self.chats: ChatManager = ChatManager(self)

    def load_config(self):
        """
        Load configuration from path specified by the framework.

        Configuration file is in YAML format.
        """
        config_path = efb_utils.get_config_path(self.channel_id)
        if not os.path.exists(config_path):
            return
        with open(config_path) as f:
            self.config: Dict[str, Any] = yaml.load(f)

    #
    # Utilities
    #

    def console_qr_code(self, uuid, status, qrcode=None):
        status = int(status)
        if self.qr_uuid == (uuid, status):
            return
        self.qr_uuid = (uuid, status)
        if status == 201:
            qr = '请在手机上确认。'
            return self.logger.log(99, qr)
        elif status == 200:
            qr = "登录成功。"
            return self.logger.log(99, qr)
        else:
            # 0: First QR code
            # 408: Updated QR code
            qr = "EWS: 请通过手机摄像头扫描该二维码。请勿使用截图。(%s, %s)\n" % (uuid, status)
            if status == 408:
                qr += "二维码已过期，请扫描新的二维码\n"
            qr += "\n"
            qr_url = "https://login.weixin.qq.com/l/" + uuid
            qr_obj = QRCode(qr_url)
            if self.flag("imgcat_qr"):
                qr_file = io.BytesIO()
                qr_obj.png(qr_file, scale=10)
                qr_file.seek(0)
                qr += self.imgcat(qr_file, "%s_QR_%s.png" % (self.channel_id, uuid))
            else:
                qr += qr_obj.terminal()
            qr += "\n若以上二维码显示不正常，请访问以下网址获取二维码：\n" \
                  "https://login.weixin.qq.com/qrcode/" + uuid
            return self.logger.log(99, qr)

    def master_qr_code(self, uuid, status, qrcode=None):
        status = int(status)
        msg = EFBMsg()
        msg.type = MsgType.Text
        msg.chat = EFBChat(self).system()
        msg.chat.chat_name = "EWS 用户登录"
        msg.author = msg.chat
        msg.deliver_to = coordinator.master

        if status == 201:
            msg.type = MsgType.Text
            msg.text = '请在手机上确认。'
        elif status == 200:
            msg.type = MsgType.Text
            msg.text = "登陆成功。"
        elif uuid != self.qr_uuid:
            msg.type = MsgType.Image
            # path = os.path.join("storage", self.channel_id)
            # if not os.path.exists(path):
            #     os.makedirs(path)
            # path = os.path.join(path, 'QR-%s.jpg' % int(time.time()))
            # self.logger.debug("master_qr_code file path: %s", path)
            file = NamedTemporaryFile(suffix=".png")
            qr_url = "https://login.weixin.qq.com/l/" + uuid
            QRCode(qr_url).png(file, scale=10)
            msg.text = '请使用手机摄像头扫描二维码。请勿使用截图。'
            msg.path = file.name
            msg.file = file
            msg.mime = 'image/png'
        if status in (200, 201) or uuid != self.qr_uuid:
            coordinator.send_message(msg)
            self.qr_uuid = uuid

    def exit_callback(self):
        self.logger.debug('Calling exit callback...')
        if self._stop_polling_event.is_set():
            return
        msg = EFBMsg()
        chat = EFBChat(self).system()
        chat.chat_type = ChatType.System
        chat.chat_name = "EWS 用户登录"
        msg.chat = msg.author = chat
        msg.deliver_to = coordinator.master
        msg.text = "微信服务器已将您登出，请在做好准备后重新登录。"
        msg.uid = "__reauth__.%s" % int(time.time())
        msg.type = MsgType.Text
        on_log_out = self.flag("on_log_out")
        on_log_out = on_log_out if on_log_out in ("command", "idle", "reauth") else "command"
        if on_log_out == "command":
            msg.type = MsgType.Text
            msg.commands = EFBMsgCommands([EFBMsgCommand(
                name="重新登录",
                callable_name="reauth",
                kwargs={"command": True}
            )])
        elif on_log_out == "reauth":
            if self.flag("qr_reload") == "console_qr_code":
                msg.text += "\n请查看您的日志或标准输出 (stdout) 以继续。"
            self.reauth()

        coordinator.send_message(msg)

    def poll(self):
        self._stop_polling_event.wait()
        # while not self.stop_polling:
        #     if not self.bot.alive:
        #         self.done_reauth.wait()
        #         self.done_reauth.clear()
        self.logger.debug("%s (%s) gracefully stopped.", self.channel_name, self.channel_id)

    def send_message(self, msg: EFBMsg) -> EFBMsg:
        """Send a message to WeChat.
        Supports text, image, sticker, and file.

        Args:
            msg (channel.EFBMsg): Message Object to be sent.

        Returns:
            This method returns nothing.

        Raises:
            EFBMessageTypeNotSupported: Raised when message type is not supported by the channel.
        """
        chat: wxpy.Chat = self.chats.get_wxpy_chat_by_uid(msg.chat.chat_uid)
        r = None
        self.logger.info("[%s] Sending message to WeChat:\n"
                         "uid: %s\n"
                         "UserName: %s\n"
                         "NickName: %s\n"
                         "Type: %s\n"
                         "Text: %s",
                         msg.uid,
                         msg.chat.chat_uid, chat.user_name, chat.name, msg.type, msg.text)

        self.logger.debug('[%s] Is edited: %s', msg.uid, msg.edit)
        if msg.edit:
            if self.flag('delete_on_edit'):
                try:
                    ews_utils.message_to_dummy_message(msg.uid, self).recall()
                except wxpy.ResponseError as e:
                    self.logger.error("[%s] Trying to recall message but failed: %s", msg.uid, e)
                    raise EFBMessageError('消息撤回失败。编辑后的消息未发送。')
            else:
                raise EFBOperationNotSupported()
        if msg.type in [MsgType.Text, MsgType.Link]:
            if isinstance(msg.target, EFBMsg):
                max_length = self.flag("max_quote_length")
                qt_txt = "%s" % msg.target.text
                if max_length > 0:
                    tgt_text = qt_txt[:max_length]
                    if len(qt_txt) >= max_length:
                        tgt_text += "…"
                    tgt_text = "「%s」" % tgt_text
                elif max_length < 0:
                    tgt_text = "「%s」" % qt_txt
                else:
                    tgt_text = ""
                if isinstance(chat, wxpy.Group) and not msg.target.author.is_self:
                    tgt_alias = "@%s\u2005 " % msg.target.author.chat_alias
                else:
                    tgt_alias = ""
                msg.text = "%s%s\n\n%s" % (tgt_alias, tgt_text, msg.text)
            r: wxpy.SentMessage = self._bot_send_msg(chat, msg.text)
            self.logger.debug('[%s] Sent as a text message. %s', msg.uid, msg.text)
        elif msg.type in (MsgType.Image, MsgType.Sticker):
            self.logger.info("[%s] Image/Sticker %s", msg.uid, msg.type)
            if msg.type != MsgType.Sticker:
                if os.fstat(msg.file.fileno()).st_size > self.MAX_FILE_SIZE:
                    raise EFBMessageError("图片体积过大。(IS01)")
                self.logger.debug("[%s] Sending %s (image) to WeChat.", msg.uid, msg.path)
                r: wxpy.SentMessage = self._bot_send_image(chat, msg.path, msg.file)
                msg.file.close()
            else:  # Convert Image format
                with NamedTemporaryFile(suffix=".gif") as f:
                    img = Image.open(msg.file)
                    try:
                        alpha = img.split()[3]
                        mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
                    except IndexError:
                        mask = Image.eval(img.split()[0], lambda a: 0)
                    img = img.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)
                    img.paste(255, mask)
                    img.save(f, transparency=255)
                    msg.path = f.name
                    self.logger.debug('[%s] Image converted from %s to GIF', msg.uid, msg.mime)
                    msg.file.close()
                    f.seek(0)
                    if os.fstat(f.fileno()).st_size > self.MAX_FILE_SIZE:
                        raise EFBMessageError("图片体积过大。(IS01)")
                    r: wxpy.SentMessage = self._bot_send_image(chat, f.name, f)
            if msg.text:
                self._bot_send_msg(chat, msg.text)
        elif msg.type in (MsgType.File, MsgType.Audio):
            self.logger.info("[%s] Sending %s to WeChat\nFileName: %s\nPath: %s\nFilename: %s",
                             msg.uid, msg.type, msg.text, msg.path, msg.filename)
            r = self._bot_send_file(chat, msg.filename, file=msg.file)
            if msg.text:
                self._bot_send_msg(chat, msg.text)
            msg.file.close()
        elif msg.type == MsgType.Video:
            self.logger.info("[%s] Sending video to WeChat\nFileName: %s\nPath: %s", msg.uid, msg.text, msg.path)
            r = self._bot_send_video(chat, msg.path, file=msg.file)
            if msg.text:
                self._bot_send_msg(chat, msg.text)
            msg.file.close()
        else:
            raise EFBMessageTypeNotSupported()

        msg.uid = ews_utils.generate_message_uid(r)
        self.logger.debug('WeChat message is assigned with unique ID: %s', msg.uid)
        return msg

    def send_status(self, status: EFBStatus):
        if isinstance(status, EFBMessageRemoval):
            if not status.message.author.is_self:
                raise EFBMessageError('只能撤回自己的消息')
            try:
                ews_utils.message_to_dummy_message(status.message.uid, self).recall()
            except wxpy.ResponseError as e:
                raise EFBMessageError('撤回失败。%s (%s)' % (e.err_msg, e.err_code))
        else:
            raise EFBOperationNotSupported()

    def get_chat_picture(self, chat: EFBChat) -> IO[bytes]:
        chat = self.chats.search_chat(uid=chat.chat_uid)
        wxpy_chat: wxpy.Chat = chat.vendor_specific['wxpy_object']
        f = None
        try:
            f = tempfile.NamedTemporaryFile(suffix='.jpg')
            wxpy_chat.get_avatar(f.name)
            f.seek(0)
            return f
        except TypeError:
            if hasattr(f, 'close', None):
                f.close()
            raise EFBOperationNotSupported()

    # Extra functions

    @extra(name="显示会话列表",
           desc="显示目前所有来自微信的会话列表。\n"
                "用法:\n    {function_name} [-r]\n"
                "    -r: 刷新列表")
    def get_chat_list(self, param: str="") -> str:
        refresh = False
        if param:
            if param == "-r":
                refresh = True
            else:
                return "未知参数：%s。" % param
        l: List[wxpy.Chat] = self.bot.chats(refresh)

        msg = "会话列表：\n"
        for (n, i) in enumerate(l):
            alias = ews_utils.wechat_string_unescape(getattr(i, 'remark_name', '') or
                                                     getattr(i, 'display_name', ''))
            name = ews_utils.wechat_string_unescape(i.nick_name)
            display_name = "%s (%s)" % (alias, name) if alias and alias != name else name
            chat_type = "?"
            if isinstance(i, wxpy.MP):
                chat_type = '公'
            elif isinstance(i, wxpy.Group):
                chat_type = '群'
            elif isinstance(i, wxpy.User):
                chat_type = '友'
            msg += "\n%s: [%s] %s" % (n, chat_type, display_name)

        return msg

    @extra(name="设置备注名称",
           desc="为微信好友设置备注名称。该操作对公众号和群组无效。\n"
                "用法:\n"
                "    {function_name} [-r] id [alias]\n"
                "    id: 会话编号，可以从「显示会话列表」中获得。\n"
                "    alias: 备注名称，留空即删除。\n"
                "    -r: 刷新列表")
    def set_alias(self, param: str="") -> str:
        refresh = False
        if param:
            if param.startswith("-r "):
                refresh = True
                param = param[2:]
            param = param.split(maxsplit=1)
            if len(param) == 1:
                cid = param[0]
                alias = ""
            else:
                cid, alias = param
        else:
            return self.set_alias.desc

        if not cid.isdecimal():
            return "编号必须为数字，您输入的是「%s」。" % cid
        else:
            cid = int(cid)

        l = self.bot.chats(refresh)

        if cid < 0:
            return "编号必须大于等于 0 且小于等于 %s。您输入了「%s」。" % (len(l) - 1, cid)

        chat = l[cid]
        if not isinstance(chat, wxpy.User):
            return "您不能为群组或公众号设置备注名称。"

        chat.set_remark_name(alias)

        if alias:
            return "好友「%s」的备注名称已设为「%s」。" % (l[cid]["NickName"], alias)
        else:
            return "好友「%s」的备注名称已移除。" % l[cid]["NickName"]

    @extra(name="登出",
           desc="登出当前微信账号。\n"
                "用法: {function_name}")
    def force_log_out(self, _: str="") -> str:
        self.bot.logout()
        self.exit_callback()
        return "Done."

    # Command functions

    def reauth(self, command=False):
        msg = "正在准备登录..."
        qr_reload = self.flag("qr_reload")
        if command and qr_reload == "console_qr_code":
            msg += "\n请查看您的日志或标准输出 (stdout) 以继续。"

        threading.Thread(target=self.authenticate, args=(qr_reload,)).start()
        return msg

    def authenticate(self, qr_reload):
        qr_callback = getattr(self, qr_reload, self.master_qr_code)
        with coordinator.mutex:
            self.bot: wxpy.Bot = wxpy.Bot(cache_path=os.path.join(efb_utils.get_data_path(self.channel_id), "wxpy.pkl"),
                                          qr_callback=qr_callback,
                                          logout_callback=self.exit_callback)
            self.bot.enable_puid(os.path.join(efb_utils.get_data_path(self.channel_id), "wxpy_puid.pkl"))
            self.done_reauth.set()

    def add_friend(self, username: str=None, verify_information: str="") -> str:
        if not username:
            return "用户名为空 (UE02)"
        try:
            self.bot.add_friend(user=username, verify_content=verify_information)
        except wxpy.ResponseError as r:
            return "处理过程中出现问题 (AF01)\n\n%s: %r" % (r.err_code, r.err_msg)
        return "已发送请求。"

    def accept_friend(self, username: str=None, verify_information: str="") -> str:
        if not username:
            return "用户名为空 (UE02)"
        try:
            self.bot.accept_friend(user=username, verify_content=verify_information)
        except wxpy.ResponseError as r:
            return "处理过程中出现问题 (AF01)\n\n%s: %r" % (r.err_code, r.err_msg)
        return "已接受请求。"

    def get_chats(self) -> List[EFBChat]:
        """
        Get all chats available from WeChat
        """
        return self.chats.get_chats()

    def get_chat(self, chat_uid: str, member_uid: Optional[str]=None) -> EFBChat:
        if member_uid:
            chat = self.chats.search_member(uid=chat_uid, member_id=member_uid)
            if not chat:
                raise EFBChatNotFound()
            else:
                return chat
        else:
            chat = self.chats.search_chat(uid=chat_uid)
            if not chat:
                raise EFBChatNotFound()
            else:
                return chat

    def stop_polling(self):
        if not self._stop_polling_event.is_set():
            self._stop_polling_event.set()
        else:
            self.done_reauth.set()

    @staticmethod
    def _bot_send_msg(chat: wxpy.Chat, message: str) -> wxpy.SentMessage:
        try:
            return chat.send_msg(message)
        except wxpy.ResponseError as e:
            raise EFBMessageError("在发送消息时发生未知错误。错误代号：%s；错误信息：%s；" % (e.err_code, e.err_msg))

    @staticmethod
    def _bot_send_file(chat: wxpy.Chat, filename: str, file: IO[bytes]) -> wxpy.SentMessage:
        try:
            return chat.send_file(filename, file=file)
        except wxpy.ResponseError as e:
            raise EFBMessageError("在发送消息时发生未知错误。错误代号：%s；错误信息：%s；" % (e.err_code, e.err_msg))

    @staticmethod
    def _bot_send_image(chat: wxpy.Chat, filename: str, file: IO[bytes]) -> wxpy.SentMessage:
        try:
            return chat.send_image(filename, file=file)
        except wxpy.ResponseError as e:
            raise EFBMessageError("在发送消息时发生未知错误。错误代号：%s；错误信息：%s；" % (e.err_code, e.err_msg))

    @staticmethod
    def _bot_send_video(chat: wxpy.Chat, filename: str, file: IO[bytes]) -> wxpy.SentMessage:
        try:
            return chat.send_video(filename, file=file)
        except wxpy.ResponseError as e:
            raise EFBMessageError("在发送消息时发生未知错误。错误代号：%s；错误信息：%s；" % (e.err_code, e.err_msg))

    @staticmethod
    def imgcat(file: io.BytesIO, filename: str) -> str:
        """
        Form a string to print in iTerm 2's ``imgcat`` format
        from a filename and a image file
        """
        def print_osc():
            if str(os.environ.get("TERM", "")).startswith("screen"):
                return "\x1bPtmux;\x1b\x1b]"
            else:
                return "\x1b]"

        def print_st():
            if str(os.environ.get("TERM", "")).startswith("screen"):
                return "\x07\x1b\\"
            else:
                return "\x07"
        res = print_osc()
        res += "1337;File=name="
        res += base64.b64encode(filename.encode()).decode()
        res += ";inline=1:"
        res += base64.b64encode(file.getvalue()).decode()
        res += print_st()
        return res
