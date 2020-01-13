
EFB 微信从端
************

.. image:: https://img.shields.io/pypi/v/efb-wechat-slave.svg
   :target: https://pypi.org/project/efb-wechat-slave/
   :alt: PyPI release

.. image:: https://github.com/blueset/efb-wechat-slave/workflows/Tests/badge.svg
   :target: https://github.com/blueset/efb-wechat-slave/actions
   :alt: Tests status

.. image:: https://pepy.tech/badge/efb-wechat-slave/month
   :target: https://pepy.tech/project/efb-wechat-slave
   :alt: Downloads per month

.. image:: https://d322cqt584bo4o.cloudfront.net/ehforwarderbot/localized.svg
   :target: https://crowdin.com/project/ehforwarderbot/
   :alt: Translate this project

.. image:: https://github.com/blueset/efb-wechat-slave/raw/master/banner.png
   :alt: Banner

.. image:: https://i.imgur.com/dCZfh14.png
   :alt: This project proudly supports #SayNoToWeChat campaign.

`其他语言的 README <.>`_.

**信道 ID**: ``blueset.wechat``

EWS 是兼容 EH Forwarder Bot 的微信从端，基于逆向工程的微信网页版、修改版 ``wxpy`` 和 ``ItChat``。

本项目的部分代码修改自 `youfou/wxpy
<https://github.com/youfou/wxpy>`_、`littlecodersh/ItChat
<https://github.com/littlecodersh/ItChat/>`_。


Alpha 版本
==========

该从端非稳定版本，且其功能随时可能会被更改。


注意
====

Since mid-2016, we have received feedback where some users’ access to
Web WeChat was banned. Most of the users were unbanned within 1 day to
3 months. When a user is banned for Web WeChat access, a pop up would
be shown when they try to use it, stating that they “cannot use Web
WeChat temporary”, and are recommended to use mobile app or
Windows/macOS instead. By observation, only less than 10% of the users
are being banned from Web WeChat during their usage.

另外，有报告称，在 2016 年年中之后注册的微信帐户「出于安全原因」无法使用网页版微信。在设置 EWS 之前，请确认您的账号是否可以使用
`网页版微信 <https://web.wechat.com/>`_ 。

该封禁不影响其他客户端的登录。目前封禁的原因尚不明确。

请谨慎使用，如果您对微信网页版有着特殊需要，请慎用此信道。详细信息请参见 `issue #7
<https://github.com/blueset/efb-wechat-slave/issues/7>`_ 。


依赖
====

* Python >= 3.6

* EH Forwarder Bot >= 2.0.0

* ffmpeg

* libmagic

* pillow


安装并启用
==========

1. 安装所需的依赖

2. 安装从端

    ::
       pip3 install efb-wechat-slave

3. Enable EWS using the *EFB configuration wizard* or in
    ``config.yaml`` of the current profile.

    当前配置文件夹的位置会根据用户的设定而改变。

    **(In EFB 2, the default configuration directory is**
    ``~/.ehforwarderbot/profiles/default`` **)**


其他安装方式
------------

社区也贡献了其他的 ETM 安装方式，包括：

* `KeLiu <https://github.com/specter119>`_ 维护的 `AUR 软件包
  <https://aur.archlinux.org/packages/python-efb-telegram-master-git>`_
  (``python-efb-telegram-master-git``)

* 其他\ `安装脚本和容器（Docker 等）
  <https://efb-modules.1a23.studio#scripts-and-containers-eg-docker>`_


可选配置
========

EWS 支持使用可选的配置文件来启用实验功能。配置文件存储于 \
``<当前配置档案文件夹>/blueset.wechat/config.yaml``。


示例配置
--------

::

   # Experimental flags
   # This section can be used to enable experimental functionality.
   # However, those features may be changed or removed at any time.
   # Options in this section is explained afterward.
   flags:
       option_one: 10
       option_two: false
       option_three: "foobar"


常见问题
========

* **如何切换已登录的微信账号？** 请登出当前的账号，并使用其他的微信手机登录。

* **如何登录两个微信账号？** 请在 EFB 配置档案中指定不同的实例 ID。

* **EWS 稳定吗？** EWS 依赖于上游项目 `ItChat
  <https://github.com/littlecodersh/ItChat>`_ 以及微信网页版的协议。根据 `ItChat
  FAQ <https://itchat.readthedocs.io/zh/latest/FAQ/>`_
  的说明，在满足以下情况的条件下，微信登录能够保持数个月稳定登录:

  * 服务器有稳定的网络连接，并且

  * **保持手机客户端长期在线。**


已知问题
========

* 就于微信网页版的工作原理，目前对于没有名称的会话、以及重名的会话支持较差，可能会有消息传递错误等问题。

* 同理，部分情况下变更名称的会话会被视为全新的会话，而「旧会话」随即消失。

* EWS 只支持网页版微信所支持的功能。这意味着：- 没有“朋友圈”功能 - 没有转账功能 - 不能发送语音消息 - 不能发送定位 等等。

* 部分文件、图片、表情等多媒体文件会被网页版微信截断，即收不到任何数据，尤以表情为甚。因此造成的偶发现象，会提醒用户使用移动客户端查看。


实验性功能
==========

以下的实验性功能随时可能被更改或被删除，请自行承担相关风险。

* ``refresh_friends`` *(bool)* [默认: ``false``]

  每次查询时强制刷新整个聊天列表。

* ``first_link_only`` *(bool)* [默认: ``false``]

  当消息包含多个文章时，仅发送第一篇文章的链接。

* ``max_quote_length`` *(int)* [默认: ``-1``]

  引用消息的长度限制。设置为 ``0`` 以禁用报价。设置为 ``-1`` 以包含全部引用的消息

* ``qr_reload`` *(str)* [默认: ``"master_qr_code"``]

  重新登录时使用的登录方式。选项：

  * 将二维码和提示输出到系统标准输出（``stdout``）。

  * 将二维码和提示发送到主端。 **注意** 登录时二维码会频繁刷新，请注意二维码可能会导致刷屏。

* ``on_log_out`` *(str)* [默认: ``"command"``]

  微信服务器将用户登出时的操作。选项：

  * ``"idle"``：仅通知用户。

  * ``"reauth"``：通知用户，并立即开始重新登录。

  * ``"command"``：通知用户，并等待用户启动重新登录过程。

* ``imgcat_qr`` *(bool)* [默认: ``false``]

  使用 `iTerm2 图像协议 <https://www.iterm2.com/documentation-images.html>`_
  显示二维码。本功能只适用于 iTerm2 用户。

* ``delete_on_edit`` *(bool)* [默认: ``false``]

  以撤回并重新发送的方式代替编辑消息。默认禁止编辑消息。

* ``app_shared_link_mode`` *(str)* [默认：``"ignore"``]

  在收到第三方合作应用分享给微信的链接时，其附带的预览图以何种形式发送。

  * ``"ignore"``：忽略略缩图

  * ``"upload"``：将缩略图上传到公开图床（https://sm.ms），并在日志中输出图片的删除链接。

  * ``"image"``：将消息以图片形式发送（不推荐）

* ``puid_logs`` *(str)* [默认：``null``]

  输出 PUID 相关日志到指定日志路径。请使用绝对路径。PUID 日志可能会根据会话数量和消息吞吐量而占用大量存储空间。

* ``send_image_as_file`` *(bool)* [默认：``false``]

  以 JPEG 图片方式发送自定义表情和 GIF，用于临时绕过微信网页版的自定义表情限制。详见 `#48
  <https://ews.1a23.studio/issues/48>`_。

* ``system_chats_to_include`` *(list of str)** [默认: ``[filehelper]``]

  在默认会话列表中显示的特殊系统会话。其内容仅能为
  ``filehelper``（文件传输助手）、``fmessage``（朋友推荐消息）、``newsapp``（腾讯新闻）、``weixin``（微信团队）其中零到四个选项。

* ``user_agent`` *(str)* [默认值: ``null``]

  指定访问网页版微信时使用的用户代理（user agent）字符串。不指定时则使用 ``itchat`` 提供的默认值。


供应商特定选项（``vendor_specific``）
=====================================

``Chat`` from EWS provides the following ``vendor_specific`` items:

* ``is_mp`` *(bool)* 该会话是否为公众号。

* ``is_contact`` *(bool)* 不明。提取自 API。

* ``is_blacklist_contact`` *(bool)* 该用户是否被加入黑名单。

* ``is_conversation_contact`` *(bool)* 不明。提取自 API。

* ``is_room_contact_del`` *(bool)* 不明。提取自 API。

* ``is_room_owner`` *(bool)* 该用户是否为群组创建者。

* ``is_brand_contact`` *(bool)* 不明。提取自 API。

* ``is_sp_contact`` *(bool)* 不明。提取自 API。

* ``is_shield_user`` *(bool)* 不明。提取自 API。

* ``is_muted`` *(bool)* 该会话是否在微信中开启免打扰。

* ``is_top`` *(bool)* 该会话是否在微信中被置顶。

* ``has_photo_album`` *(bool)* 不明。提取自 API。


许可协议
========

EWS 使用了 `GNU Affero General Public License 3.0
<https://www.gnu.org/licenses/agpl-3.0.txt>`_ 或更新版本作为其开源许可:

::

   EFB WeChat Slave Channel: A slave channel for EH Forwarder Bot.
   Copyright (C) 2016 - 2020 Eana Hufwe, and the EFB WeChat Slave Channel contributors
   All rights reserved.

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU Affero General Public License as
   published by the Free Software Foundation, either version 3 of the
   License, or any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU Affero General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.


翻译支持
========

EWS 支持了界面本地化翻译。您可以将语言环境变量（``LANGUAGE``、``LC_ALL``、``LC_MESSAGES`` 或
``LANG``）设为一种\ `已支持的语言
<https://crowdin.com/project/ehforwarderbot/>`_。同时，您也可以在我们的 `Crowdin
页面 <https://crowdin.com/project/ehforwarderbot/>`_\ 里将 EWS 翻译为您的语言。

備註: 如果您使用源代码安装，您需要手动编译翻译字符串文件（``.mo``）才可启用翻译后的界面。
