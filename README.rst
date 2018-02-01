EFB WeChat Slave Channel：EFB 微信从端 (EWS)
============================================

.. badges

.. figure:: https://i.imgur.com/dCZfh14.png
   :alt: This project proudly supports #SayNoToWeChat campaign.

**Channel ID**: ``blueset.wechat``

EWS 是兼容 EH Forwarder Bot 的微信从端，基于逆向工程的微信网页版、
修改版 ``wxpy``\ ，\ ``itchat``\ 。

本项目的部分代码修改自
`youfou/wxpy <https://github.com/youfou/wxpy>`__\ 。

Alpha 版本
----------

本项目目前仍是 Alpha 版本，仍不稳定，且功能可能随时变更。

开发进度减缓
------------

由于技术原因（见注释），EWS 开发进度将会减缓。恢复时间未定。

..  那个垃圾网页版 WC 把俺的账号给封了。
    只能坐等给恢复了。顺便求恢复方法或者完全封号的方法。
    （是的俺就想作个大死）

使用前须知
----------

自 2016 年中旬以来，陆续有用户报告其微信网页版登录被腾讯封禁。
表现为用任何方式登录微信网页版提示「当前登录环境异常。为了你的账号安全，
暂时不能登录 Web 微信。你可以通过手机客户端或 Windows 微信登录」
或类似的提示。只有不到半数的用户在封禁后通过各种方式恢复，但仍有相当数量的
用户还没有被解封。该封禁不影响其他客户端的登录。目前封禁的原因尚不明确。

如果你对网页版登录有要求的话，请慎用此 Channel。详细的相关信息请参见
项目 Wiki。

软件依赖
--------

-  Python >= 3.6
-  EH Forwarder Bot >= 2.0.0
-  ffmpeg
-  libmagic
-  pillow

安装与启用
----------

1. 安装如上所要求的二进制依赖
2. 安装

   .. code:: shell

       pip3 install efb-wechat-slave

3. 在当前配置文件夹 (Profile) 的 ``config.yaml`` 中启用 EWS。

   当前配置文件夹的位置会根据用户的设定而改变。

   **(EFB 2.0.0a1 中，默认的配置文件夹位于**
   ``~/.ehforwarderbot/profiles/default`` **)**

可选的配置文件
--------------

EWS 支持使用可选的配置文件来启用实验功能。配置文件存储于
``<当前配置文件夹>/blueset.wechat/config.yaml``\ 。

配置文件例
~~~~~~~~~~

.. code:: yaml

    # 实验功能
    # 使用本段来调整实验功能的设置。请注意实验功能随时可能变更或失效。
    # 详细说明见下文。
    flags:
        option_one: 10
        option_two: false
        option_three: "foobar"

常见问题
--------

-  **如何切换已登录的微信账号？**
   请登出当前的账号，并使用其他的微信手机登录。
-  **如何登录两个微信账号？**
   该功能没有正式支持，并需要使用者具有一定的技术能力。操作方法请参见项目
   Wiki。
-  **EWS 稳定吗？**
   EWS 依赖于上游项目
   `ItChat <https://github.com/littlecodersh/ItChat>`__
   以及微信网页版的协议。根据 `ItChat
   FAQ <https://itchat.readthedocs.io/zh/latest/FAQ/>`__
   的说明，在满足以下情况的条件下，微信登录能够保持数个月稳定登录:

   -  服务器有稳定的网络连接，并且
   -  **保持手机客户端长期在线。**

已知问题
--------

- 就于微信网页版的工作原理，目前对于没有名称的会话、以及重名的会话支持较差，
  可能会有消息传递错误等问题。
- 同理，部分情况下变更名称的会话会被视为全新的会话，而「旧会话」随即消失。
- 仅支持微信网页版所支持的功能以及消息类型，即
    - 没有朋友圈
    - 没有红包
    - 不能发语音
    - 不能发位置
    - ……等等诸如此类
- 部分文件、图片、表情等多媒体文件会被网页版微信截断，即收不到任何数据，
  尤以表情为甚。因此造成的偶发现象，会提醒用户使用移动客户端查看。


实验功能
--------

以下的实验功能可能不稳定，并可能随时更改、删除。使用时请注意。

-  ``refresh_friends`` *(bool)* [默认值: ``false``]

   每当请求会话列表时，强制刷新会话列表。

-  ``first_link_only`` *(bool)* [默认值: ``false``]

   在收到多链接消息时，仅发送第一条链接。默认多链接会发送多条消息。

-  ``max_quote_length`` *(int)* [默认值: ``-1``]

   引用消息中引文的长度限制。设置为 0 关闭引文功能。设置为 -1
   则对引文长度不做限制。

-  ``qr_reload`` *(str)* [默认值: ``"master_qr_code"``]

   重新登录时使用的登录方式：
   选项:

   -  ``"console_qr_code"``:
      将二维码和提示输出到系统标准输出（\ ``stdout``\ ）。
   -  ``"master_qr_code"``: 将二维码和提示发送到主端。 **注意**
      登录时二维码会频繁刷新，请注意二维码可能会导致刷屏。

-  ``on_log_out`` *(str)* [默认值: ``"command"``]

   微信服务器将用户登出时的操作。
   选项:

   -  ``"idle"``: 仅通知用户。
   -  ``"reauth"``: 通知用户，并立即开始重新登录。
   -  ``"command"``: 通知用户，并等待用户启动重新登录过程。

-  ``imgcat_qr`` *(bool)* [默认值: ``false``]

   使用 `iTerm2
   图像协议 <https://www.iterm2.com/documentation-images.html>`__
   显示二维码。本功能只适用于 iTerm2 用户。

-  ``delete_on_edit`` *(bool)* [默认值: ``false``]

   以撤回并重新发送的方式代替编辑消息。默认禁止编辑消息。

-  ``app_shared_link_mode`` *(str)* [默认值：``"ignore"``]

   在收到第三方合作应用分享给微信的链接时，其附带的预览图以何种形式发送。

   -  ``"ignore"``\ ：忽略附带的缩略图
   -  ``"upload"``\ ：将缩略图上传到公开图床（\ https://sm.ms\ ），并在日志中输出图片的删除链接。
   -  ``"image"``\ ：将消息以图片形式发送（不推荐）

``vendor_specific``
-------------------

EWS 的 ``EFBChat`` 提供了以下的 ``vendor_specific`` 项目：

-  ``is_mp`` *(bool)*
   该会话是否为公众号。
-  ``wxpy_objet`` *(wxpy.Chat)*
   该会话所对应的 ``wxpy.Chat`` 对象。
