from gettext import translation
from io import StringIO

import cjkwrap
from bullet import YesNo, Numbers, Bullet, Check
from pkg_resources import resource_filename
from ruamel.yaml import YAML

from ehforwarderbot import coordinator, utils
from ehforwarderbot.types import ModuleID
from . import WeChatChannel


def print_wrapped(text):
    paras = text.split("\n")
    for i in paras:
        print(*cjkwrap.wrap(i), sep="\n")


translator = translation("efb_wechat_slave",
                         resource_filename('efb_wechat_slave', 'locale'),
                         fallback=True)

_ = translator.gettext
ngettext = translator.ngettext


class DataModel:
    data: dict

    def __init__(self, profile: str, instance_id: str):
        coordinator.profile = profile
        self.profile = profile
        self.instance_id = instance_id
        self.channel_id = WeChatChannel.channel_id
        if instance_id:
            self.channel_id = ModuleID(self.channel_id + "#" + instance_id)
        self.config_path = utils.get_config_path(self.channel_id)
        self.yaml = YAML()
        if not self.config_path.exists():
            self.build_default_config()
        else:
            self.data = self.yaml.load(self.config_path.open())

    def build_default_config(self):
        s = _(
            # TRANSLATORS: This part of text must be formatted in a monospaced font and no line shall exceed the width of a 70-cell-wide terminal.
            "# ===========================================\n"
            "# EFB WeChat Slave Channel Configuration File\n"
            "# ===========================================\n"
            "#\n"
            "# This file can help you to adjust some experimental features provided in\n"
            "# EWS. It is not required to have this file for EWS to work.\n"
        )
        s += "\n"
        s += "flags: {}"

        str_io = StringIO(s)
        str_io.seek(0)
        self.data = self.yaml.load(str_io)

    def save(self):
        with self.config_path.open('w') as f:
            self.yaml.dump(self.data, f)


flags_settings = {
    "refresh_friends":
        (False, 'bool', None,
         _('Force refresh the entire chat list every time when queried.'
           )),
    "first_link_only":
        (False, 'bool', None,
         _('Send only the first article link when a message contains '
           'multiple articles.'
           )),
    "max_quote_length":
        (-1, 'int', None,
         _('Length limit of quoted message. Set to 0 to disable quotation. '
           'Set to -1 to include the full quoted message'
           )),
    "qr_reload":
        ("master_qr_code", 'str', ['master_qr_code', 'console_qr_code'],

         _('Method to log in when you are logged out while EWS is running.\n'
           'Options:\n'
           '\n'
           '-  "console_qr_code": Send QR code to standard output (stdout).\n'
           '-  "master_qr_code": Send QR code to master channel. \n'
           '        Note: QR code might change frequently.'
           )),
    "on_log_out":
        ("idle", 'choices', ['idle', 'reauth', 'command'],
         _('Behavior when WeChat server logged your account out.\n'
           '\n'
           'Options:\n'
           '-  "idle": Only notify the user.\n'
           '-  "reauth": Notify the user and start log in immediately.\n'
           '-  "command": Notify the user, and wait for user to start '
           'log in manually.'
           )),
    "imgcat_qr":
        (False, 'bool', None,
         _('Use iTerm2 image protocol to show QR code. This is only '
           'applicable to iTerm 2 users.'
           )),
    "delete_on_edit":
        (False, 'bool', None,
         _('Turn on to edit message by recall and resend. Edit message is '
           'disabled by default.'
           )),
    "app_shared_link_mode":
        ("ignore", 'choices', ['ignore', 'upload', 'image'],
         _('Behavior to deal with thumbnails when a message shared by 3rd '
           'party apps is received.\n'
           '\n'
           '-  "ignore": Ignore thumbnail\n'
           '-  "upload": Upload to public image hosting (https://sm.ms), '
           'and output its delete link to the log.\n'
           '-  "image": Send thumbnail as image (not recommended).'
           )),
    "puid_logs":
        (None, 'path', None,
         _(
             'Output PUID related log to the path indicated. Please use '
             'absolute path. In case of high volume of messages and chats, '
             'PUID log may occupy a large amount of space.'
             )),
    "send_stickers_and_gif_as_jpeg":
        (False, 'bool', None,
         _('Send stickers and GIF images as JPEG to bypass Web WeChat custom '
           'sticker limits as a workaround.'
           )),
    "system_chats_to_include":
        (["filehelper"], 'multiple', ['filehelper', 'fmessage', 'newsapp', 'weixin'],
         _(
             'List of system chats to show in the default chat list. '
             'It must be zero to four of the following: filehelper '
             '(File Helper), fmessage (Friend suggestions), newsapp '
             '(Tencent News) and, weixin (WeChat Team).'
        )),
    "user_agent":
        (None, 'str', None,
         _('Choose the User Agent string to use when accessing Web Wechat. '
           'Leave undefined to use the default value provided by itchat.'
           )),
    "text_post_processing":
        (True, 'bool', None,
         _('Determine whether to post-process text of messages received from '
           'WeChat.'
           )),
}


def setup_experimental_flags(data):
    print_wrapped(_(
        "EWS does not require any configuration, you only need to scan "
        "a QR code when you start up EH Forwarder Bot. It’s as simple as "
        "that.\n"
        "\n"
        "We have provided some experimental features that you can use. "
        "They are not required to be enabled for EWS to work. If you do not "
        "want to enable these feature, just press ENTER, and you are good to go."
    ))

    widget = YesNo(prompt=_("Do you want to config experimental features? "),
                   prompt_prefix="[yN] ", default="n")
    if not widget.launch():
        return

    for key, value in flags_settings.items():
        default, cat, params, desc = value
        if data.data['flags'].get(key) is not None:
            default = data.data['flags'].get(key)
        print()
        print(key)
        print_wrapped(desc)
        if cat == 'bool':
            prompt_prefix = '[Yn] ' if default else '[yN] '
            ans = YesNo(prompt=f"{key}? ",
                        prompt_prefix=prompt_prefix,
                        default='y' if default else 'n') \
                .launch()

            data.data['flags'][key] = ans
        elif cat == 'int':
            ans = Numbers(prompt=f"{key} [{default}]? ", type=int) \
                .launch(default=default)
            data.data['flags'][key] = ans
        elif cat == 'choices':
            try:
                assert isinstance(params, list)
                default = params.index(default)
            except ValueError:
                default = 0
            ans = Bullet(prompt=f"{key}?", choices=params) \
                .launch(default=default)
            data.data['flags'][key] = ans
        elif cat == 'multiple':
            default_idx = []
            assert isinstance(params, list)
            for i in default:
                try:
                    default_idx.append(params.index(i))
                except ValueError:
                    pass
            ans = Check(
                prompt=f"{key}?",
                choices=params
            ).launch(default=default_idx)
            data.data['flags'][key] = ans
        elif cat == 'str':
            ans = input(f"{key} [{default}]: ")
            data.data['flags'][key] = ans or default
        else:
            print(_("Skipped."))

    print(_("Saving configurations..."), end="", flush=True)
    data.save()
    print(_("OK"))


def wizard(profile, instance_id):
    data = DataModel(profile, instance_id)

    print_wrapped(_(
        "=====================================\n"
        "EFB WeChat Slave Channel Setup Wizard\n"
        "=====================================\n"
    ))
    if translator.info().get('language') != 'zh_CN':
        print_wrapped("需要显示中文？请将系统语言（或语言环境变量）\n"
                      "设置为「中文（中国）」（zh_CN）。")
        print()

    setup_experimental_flags(data)

    print()
    print_wrapped(_(
        "Congratulations! You have finished the setup wizard for EFB WeChat "
        "Slave channel."
    ))
