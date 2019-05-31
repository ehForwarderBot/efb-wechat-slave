EFB WeChat Slave Channel
========================

.. image:: https://img.shields.io/pypi/v/efb-wechat-slave.svg
   :alt: PyPI release
   :target: https://pypi.org/project/efb-wechat-slave/
.. image:: https://d322cqt584bo4o.cloudfront.net/ehforwarderbot/localized.svg
   :alt: Translate this project
   :target: https://crowdin.com/project/ehforwarderbot/

.. figure:: https://i.imgur.com/dCZfh14.png
   :alt: This project proudly supports #SayNoToWeChat campaign.

`README in other languages`_.

.. _README in other languages: .

**Channel ID**: ``blueset.wechat``

EWS is an EFB Slave Channel for WeChat, based on reversed engineered
WeChat Web API, modified ``wxpy``, and ``itchat``.

Some source code in this repository was adapted from
`youfou/wxpy <https://github.com/youfou/wxpy>`__.

Alpha Version
-------------

This is an unstable alpha version, and its functionality may change at any
time.

Attention
---------

Since mid-2016, we have received feedback where some users' access to Web
WeChat was banned. Most of the users were unbanned within 1 week to 3 months.
When a user is banned for Web WeChat access, a pop up would be shown when
they try to use it, stating that they "cannot use Web WeChat temporary", and
are recommended to "use mobile app or Windows/macOS instead".

The ban will NOT affect your access to any other client. The cause of such ban
is not clear.

Please proceed with caution, and avoid using this Channel if you have special
need of Web WeChat access. Learn more in the Project Wiki.

Dependencies
------------

-  Python >= 3.6
-  EH Forwarder Bot >= 2.0.0
-  ffmpeg
-  libmagic
-  pillow

Install and Enable
----------

1. Install all binary dependencies stated above
2. Install

   .. code:: shell

       pip3 install efb-wechat-slave

3. Enable EWS in ``config.yaml`` of the current profile.

   The config directory may vary based on your settings.

   **(In EFB 2.0.0a1, the default configuration directory is**
   ``~/.ehforwarderbot/profiles/default`` **)**

Optional configuration
----------------------

You can enable experimental features by creating a configuration
file, which is located at
``<directory to current profile>/blueset.wechat/config.yaml``.

Example configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

    # Experimental flags
    # This section can be used to enable experimental functionality.
    # However, those features may be changed or removed at any time.
    # Options in this section is explained afterward.
    flags:
        option_one: 10
        option_two: false
        option_three: "foobar"

FAQ
---

-  **How to switch to another WeChat account?**
   Please log out from your phone, and log in again with another one.
-  **How to log in with multiple WeChat accounts?**
   Please indicate different Instance ID in the profile's config file.
-  **Is EWS stable?**
   EWS depends on
   `ItChat <https://github.com/littlecodersh/ItChat>`__
   project and Web WeChat protocol. According to `ItChat
   FAQ <https://itchat.readthedocs.io/zh/latest/FAQ/>`__
   a stable session that lasts over months is possible when you:

   -  have a stable internet connection on your server, and
   -  **keep your WeChat app always online**.

Known Issues
------------

- Due to the design of Web WeChat, chats with no name
  or identical name might be identified as the same chat,
  which might lead to misdelivery of messages.
- Similarly, in limited situations, a chat will be seen as
  a "new chat" when its name is changed, and the "old chat"
  is thus disappeared.
- Only features supported by Web WeChat are supported by EWS,
  which means:
    - No "Moments"
    - No money transfers
    - Cannot send voice messages
    - Cannot send locations
    - etc.
- Some multimedia files (pictures, stickers, files, etc.) might be
  blocked by Web WeChat, and no data is received, especially for
  stickers. In such cases, you will be reminded to check your phone.


Experimental features
---------------------

The following flags are experimental features, may change, break, or
disappear at any time. Use at your own risk.


-  ``refresh_friends`` *(bool)* [Default: ``false``]

   Force refresh the entire chat list every time when queried.

-  ``first_link_only`` *(bool)* [Default: ``false``]

   Send only the first article link when a message contains multiple articles.

-  ``max_quote_length`` *(int)* [Default: ``-1``]

   Length limit of quoted message. Set to ``0`` to disable quotation.
   Set to ``-1`` to include the full quoted message

-  ``qr_reload`` *(str)* [Default: ``"master_qr_code"``]

   Method to log in when you are logged out while EWS is running.
   Options:

   -  ``"console_qr_code"``:
      Send QR code to standard output (``stdout``).
   -  ``"master_qr_code"``: Send QR code to master channel. **Note:**
      QR code might change frequently.

-  ``on_log_out`` *(str)* [Default: ``"command"``]

   Behavior when WeChat server logged your account out.
   Options:

   -  ``"idle"``: Only notify the user.
   -  ``"reauth"``: Notify the user and start log in immediately.
   -  ``"command"``: Notify the user, and wait for user to start
      log in manually.

-  ``imgcat_qr`` *(bool)* [Default: ``false``]

   Use `iTerm2
   image protocol <https://www.iterm2.com/documentation-images.html>`__
   to show QR code. This is only applicable to iTerm 2 users.

-  ``delete_on_edit`` *(bool)* [Default: ``false``]

   Turn on to edit message by recall and resend. Edit message is disabled by default.

-  ``app_shared_link_mode`` *(str)* [Default：``"ignore"``]

   Behavior to deal with thumbnails when a message shared by 3rd party apps is received.

   -  ``"ignore"``\ ：Ignore thumbnail
   -  ``"upload"``\ ：Upload to public image hosting (https://sm.ms ), and output
      its delete link to the log.
   -  ``"image"``\ ：Send thumbnail as image (not recommended).

-  ``puid_logs`` *(str)* [Default：``null``]

   Output PUID related log to the path indicated. Please use absolute path.
   In case of high volume of messages and chats, PUID log may occupy a large amount
   of space.

``vendor_specific``
-------------------

``EFBChat`` from EWS provides the following ``vendor_specific`` items:

-  ``is_mp`` *(bool)*
   If the chat is an "Official Account".
-  ``wxpy_objet`` *(wxpy.Chat)*
   The corresponding ``wxpy.Chat`` object of the chat.

Experimental localization support
---------------------------------

EWS supports localized user interface prompts experimentally,
by setting the locale environmental variable (``LANGUAGE``,
``LC_ALL``, ``LC_MESSAGES`` or ``LANG``) to one of our
`supported languages`_. Meanwhile, you can help to translate
this project into your languages on `our Crowdin page`_.

.. _supported languages: https://crowdin.com/project/ehforwarderbot/
.. _our Crowdin page: https://crowdin.com/project/ehforwarderbot/