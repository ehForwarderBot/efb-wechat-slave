# coding: utf-8

from typing import Dict, Any, TYPE_CHECKING

import itchat.utils

from . import wxpy
if TYPE_CHECKING:
    from . import WeChatChannel

WC_EMOTICON_CONVERSION = {
    '[微笑]': '😃',    '[Smile]': '😃',
    '[撇嘴]': '😖',    '[Grimace]': '😖',
    '[色]': '😍',      '[Drool]': '😍',
    '[发呆]': '😳',    '[Scowl]': '😳',
    '[得意]': '😎',    '[Chill]': '😎',
    '[流泪]': '😭',    '[Sob]': '😭',
    '[害羞]': '☺️',    '[Shy]': '☺️',
    '[闭嘴]': '🤐',    '[Shutup]': '🤐',
    '[睡]': '😴',      '[Sleep]': '😴',
    '[大哭]': '😣',    '[Cry]': '😣',
    '[尴尬]': '😰',    '[Awkward]': '😰',
    '[发怒]': '😡',    '[Pout]': '😡',
    '[调皮]': '😜',    '[Wink]': '😜',
    '[呲牙]': '😁',    '[Grin]': '😁',
    '[惊讶]': '😱',    '[Surprised]': '😱',
    '[难过]': '🙁',    '[Frown]': '🙁',
    '[囧]': '☺️',      '[Tension]': '☺️',
    '[抓狂]': '😫',    '[Scream]': '😫',
    '[吐]': '🤢',      '[Puke]': '🤢',
    '[偷笑]': '😅',    '[Chuckle]': '😅',
    '[愉快]': '☺️', '[Joyful]': '☺️',
    '[白眼]': '🙄', '[Slight]': '🙄',
    '[傲慢]': '😕', '[Smug]': '😕',
    '[困]': '😪', '[Drowsy]': '😪',
    '[惊恐]': '😱', '[Panic]': '😱',
    '[流汗]': '😓', '[Sweat]': '😓',
    '[憨笑]': '😄', '[Laugh]': '😄',
    '[悠闲]': '😏', '[Loafer]': '😏',
    '[奋斗]': '💪', '[Strive]': '💪',
    '[咒骂]': '😤', '[Scold]': '😤',
    '[疑问]': '❓', '[Doubt]': '❓',
    '[嘘]': '🤐', '[Shhh]': '🤐',
    '[晕]': '😲', '[Dizzy]': '😲',
    '[衰]': '😳', '[BadLuck]': '😳',
    '[骷髅]': '💀', '[Skull]': '💀',
    '[敲打]': '👊', '[Hammer]': '👊',
    '[再见]': '🙋\u200d♂', '[Bye]': '🙋\u200d♂',
    '[擦汗]': '😥', '[Relief]': '😥',
    '[抠鼻]': '🤷\u200d♂', '[DigNose]': '🤷\u200d♂',
    '[鼓掌]': '👏', '[Clap]': '👏',
    '[坏笑]': '👻', '[Trick]': '👻',
    '[左哼哼]': '😾', '[Bah！L]': '😾',
    '[右哼哼]': '😾', '[Bah！R]': '😾',
    '[哈欠]': '😪', '[Yawn]': '😪',
    '[鄙视]': '😒', '[Lookdown]': '😒',
    '[委屈]': '😣', '[Wronged]': '😣',
    '[快哭了]': '😔', '[Puling]': '😔',
    '[阴险]': '😈', '[Sly]': '😈',
    '[亲亲]': '😘', '[Kiss]': '😘',
    '[可怜]': '😻', '[Whimper]': '😻',
    '[菜刀]': '🔪', '[Cleaver]': '🔪',
    '[西瓜]': '🍉', '[Melon]': '🍉',
    '[啤酒]': '🍺', '[Beer]': '🍺',
    '[咖啡]': '☕', '[Coffee]': '☕',
    '[猪头]': '🐷', '[Pig]': '🐷',
    '[玫瑰]': '🌹', '[Rose]': '🌹',
    '[凋谢]': '🥀', '[Wilt]': '🥀',
    '[嘴唇]': '💋', '[Lip]': '💋',
    '[爱心]': '❤️', '[Heart]': '❤️',
    '[心碎]': '💔', '[BrokenHeart]': '💔',
    '[蛋糕]': '🎂', '[Cake]': '🎂',
    '[炸弹]': '💣', '[Bomb]': '💣',
    '[便便]': '💩', '[Poop]': '💩',
    '[月亮]': '🌃', '[Moon]': '🌃',
    '[太阳]': '🌞', '[Sun]': '🌞',
    '[拥抱]': '🤗', '[Hug]': '🤗',
    '[强]': '👍', '[Strong]': '👍',
    '[弱]': '👎', '[Weak]': '👎',
    '[握手]': '🤝', '[Shake]': '🤝',
    '[胜利]': '✌️', '[Victory]': '✌️',
    '[抱拳]': '🙏', '[Salute]': '🙏',
    '[勾引]': '💁\u200d♂', '[Beckon]': '💁\u200d♂',
    '[拳头]': '👊', '[Fist]': '👊',
    '[OK]': '👌',
    '[跳跳]': '💃', '[Waddle]': '💃',
    '[发抖]': '🙇', '[Tremble]': '🙇',
    '[怄火]': '😡', '[Aaagh!]': '😡',
    '[转圈]': '🕺', '[Twirl]': '🕺',
    '[嘿哈]': '🤣', '[Hey]': '🤣',
    '[捂脸]': '🤦\u200d♂', '[Facepalm]': '🤦\u200d♂',
    '[奸笑]': '😜', '[Smirk]': '😜',
    '[机智]': '🤓', '[Smart]': '🤓',
    '[皱眉]': '😟', '[Concerned]': '😟',
    '[耶]': '✌️', '[Yeah!]': '✌️',
    '[红包]': '💰', '[Packet]': '💰',
    '[鸡]': '🐥', '[Chick]': '🐥',
    '[蜡烛]': '🕯️', '[Candle]': '🕯️',
    '[Thumbs Up]': '👍', '[Pleased]': '😊',
    '[Rich]': '🀅',
    '[Pup]': '🐶',
}


class ExperimentalFlagsManager:
    DEFAULT_VALUES = {
        'refresh_friends': False,
        'first_link_only': False,
        'max_quote_length': -1,
        'qr_reload': 'master_qr_code',
        'on_log_out': 'command',
        'imgcat_qr': False,
        'delete_on_edit': False,
        'app_shared_link_mode': 'ignore',
        'puid_logs': None,
        'send_stickers_and_gif_as_jpeg': True
    }

    def __init__(self, channel: 'WeChatChannel'):
        self.config: Dict[str, Any] = ExperimentalFlagsManager.DEFAULT_VALUES.copy()
        self.config.update(channel.config.get('flags', dict()))

    def __call__(self, flag_key: str) -> Any:
        if flag_key not in self.config:
            raise ValueError("%s is not a valid experimental flag" % flag_key)
        return self.config[flag_key]


def wechat_string_unescape(content: str) -> str:
    """
    Unescape a WeChat HTML string.

    Args:
        content (str): String to be formatted

    Returns:
        str: Unescaped string.
    """
    if not content:
        return ""
    d = {"Content": content}
    itchat.utils.msg_formatter(d, "Content")
    for i in WC_EMOTICON_CONVERSION:
        d['Content'] = d['Content'].replace(i, WC_EMOTICON_CONVERSION[i])
    return d['Content']


def generate_message_uid(message: wxpy.SentMessage) -> str:
    return "%s %s %s" % (message.chat.puid,
                         message.id,
                         message.local_id)


def message_to_dummy_message(message_uid: str, channel: 'WeChatChannel') -> wxpy.SentMessage:
    """
    Generate a wxpy.SentMessage object with minimum identifying information.
    This is generally used to recall messages using WXPY's API without the message object

    Args:
        message_uid: puid, id, local_id joined by space
        channel: the slave channel object that issued this message
    """
    puid, m_id, l_id = message_uid.split(' ', 2)
    d = {
        'receiver': channel.chats.get_wxpy_chat_by_uid(puid),
        'id': m_id,
        'local_id': l_id
    }
    return wxpy.SentMessage(d)
