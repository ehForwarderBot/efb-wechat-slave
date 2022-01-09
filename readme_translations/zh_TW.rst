
EFB 微信從端
************

.. image:: https://img.shields.io/pypi/v/efb-wechat-slave.svg
   :target: https://pypi.org/project/efb-wechat-slave/
   :alt: PyPI release

.. image:: https://github.com/ehForwarderBot/efb-wechat-slave/workflows/Tests/badge.svg
   :target: https://github.com/ehForwarderBot/efb-wechat-slave/actions
   :alt: Tests status

.. image:: https://pepy.tech/badge/efb-wechat-slave/month
   :target: https://pepy.tech/project/efb-wechat-slave
   :alt: Downloads per month

.. image:: https://d322cqt584bo4o.cloudfront.net/ehforwarderbot/localized.svg
   :target: https://crowdin.com/project/ehforwarderbot/
   :alt: Translate this project

.. image:: https://github.com/ehForwarderBot/efb-wechat-slave/raw/master/banner.png
   :alt: Banner

.. image:: https://i.imgur.com/dCZfh14.png
   :alt: This project proudly supports #SayNoToWeChat campaign.

`其他語言的 README <.>`_.

**頻道 ID**: ``blueset.wechat``

EWS 是相容 EH Forwarder Bot 的微信從端，基於逆向工程的微信網頁版、修改版 ``wxpy`` 和 ``ItChat``。

本項目的部分程式碼修改自 `youfou/wxpy
<https://github.com/youfou/wxpy>`_、`littlecodersh/ItChat
<https://github.com/littlecodersh/ItChat/>`_。


使用前閱讀
==========

自 2017
年中旬以來，陸續有使用者報告稱其微信的網頁端被封禁。多數使用者在 1 天至 3 個月內被解封。當被封禁的使用者嘗試登入網頁端時，會彈出提示稱「目前登入環境異常。為了你的帳號安全，暫時不能登入網頁版微信。你可以透過手機用戶端或 Windows 微信登入」。據觀察，只有不到一成的使用者在使用期間被禁止使用網頁版微信。

另外，有報告稱，在 2017 年年中之後註冊的微信帳戶 「出於安全原因」 無法使用網頁版微信。在設定 EWS
之前，請確認您的帳號是否可以使用 `網頁版微信 <https://web.wechat.com/>`_ 。

該封禁不影響其他用戶端的登入。目前封禁的原因尚不明確。

請謹慎使用，如果您對微信網頁版有著特殊需要，請慎用此頻道。詳細訊息請參見 `issue #7
<https://github.com/ehForwarderBot/efb-wechat-slave/issues/7>`_ 。


依賴
====

* Python >= 3.6

* EH Forwarder Bot >= 2.0.0

* ffmpeg

* libmagic

* pillow


安裝並啟用
==========

1. 安裝所需的依賴

2. 安裝從端

    ::
       pip3 install efb-wechat-slave

3. 使用 *EFB 配置嚮導* 或目前配置檔案的 ``config.yaml`` 啟用 EWS。

    目前配置檔案夾的位置會根據使用者的設定而改變。

    **(在 EFB 2 中，預設的配置檔案夾位於** ``~/.ehforwarderbot/profiles/default``
    **）**


其他安裝方式
------------

社群也貢獻了其他的 ETM 安裝方式，包括：

* `KeLiu <https://github.com/specter119>`_ 維護的 `AUR 套裝軟體
  <https://aur.archlinux.org/packages/python-efb-telegram-master-git>`_
  (``python-efb-telegram-master-git``)

* 其他\ `安裝腳本和容器（Docker 等）
  <https://efb-modules.1a23.studio#scripts-and-containers-eg-docker>`_


可選配置
========

EWS 支援使用可選的配置檔案來啟用實驗功能。配置檔案儲存於 \
``<目前配置檔案資料夾>/blueset.wechat/config.yaml``。


範例配置
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


常見問題
========

* **如何切換已登入的微信帳號？** 請登出目前的帳號，並使用其他的微信手機登入。

* **如何登入兩個微信帳號？** 請在 EFB 配置檔案中指定不同的實例 ID。

* **EWS 穩定嗎？** EWS 依賴於上游項目 `ItChat
  <https://github.com/littlecodersh/ItChat>`_ 以及微信網頁版的協議。根據 `ItChat
  FAQ <https://itchat.readthedocs.io/zh/latest/FAQ/>`_
  的說明，在滿足以下情況的條件下，微信登入能夠保持數個月穩定登入:

  * 伺服器有穩定的網路連接，並且

  * **保持手機用戶端長期線上。**


已知問題
========

* 就於微信網頁版的工作原理，目前對於沒有名稱的對話、以及重名的對話支援較差，可能會有消息傳遞錯誤等問題。

* 同理，部分情況下變更名稱的對話會被視為全新的對話，而「舊對話」隨即消失。

* EWS 只支援網頁版微信所支援的功能。這意味著：- 沒有「朋友圈」功能 - 沒有轉帳功能 - 不能發送語音消息 - 不能發送定位 等等。

* 部分文件、圖片、表情等多媒體檔案會被網頁版微信截斷，即收不到任何資料，尤以表情為甚。因此造成的偶發現像，會提醒使用者使用移動用戶端查看。


實驗性功能
==========

以下的實驗性功能隨時可能被更改或被刪除，請自行承擔相關風險。

* ``refresh_friends`` *(bool)* [預設: ``false``]

  每次查詢時強制重新整理整個聊天列表。

* ``first_link_only`` *(bool)* [預設: ``false``]

  當消息包含多個文章時，僅發送第一篇文章的連結。

* ``max_quote_length`` *(int)* [預設: ``-1``]

  引用消息的長度限制。設定為 ``0`` 以禁用報價。設定為 ``-1`` 以包含全部引用的消息

* ``qr_reload`` *(str)* [預設: ``"master_qr_code"``]

  重新登入時使用的登入方式。選項：

  * 將二維碼和提示輸出到系統標準輸出（``stdout``）。

  * 將二維碼和提示發送到主端。 **注意** 登入時二維碼會頻繁重新整理，請注意二維碼可能會導致洗版。

* ``on_log_out`` *(str)* [預設: ``"command"``]

  微信伺服器將使用者登出時的操作。選項：

  * ``"idle"``：僅通知使用者。

  * ``"reauth"``：通知使用者，並立即開始重新登入。

  * ``"command"``：通知使用者，並等待使用者啟動重新登入過程。

* ``imgcat_qr`` *(bool)* [預設: ``false``]

  使用 `iTerm2 圖像協議 <https://www.iterm2.com/documentation-images.html>`_
  顯示二維碼。本功能只適用於 iTerm2 使用者。

* ``delete_on_edit`` *(bool)* [預設: ``false``]

  以撤回並重新髮送的方式代替編輯消息。預設禁止編輯消息。

* ``app_shared_link_mode`` *(str)* [預設：``"ignore"``]

  在收到第三方合作應用分享給微信的連結時，其附帶的預覽圖以何種形式發送。

  * ``"ignore"``：忽縮圖

  * ``"upload"``：將縮圖上傳到公開圖床（https://sm.ms），並在日誌中輸出圖片的刪除連結。

  * ``"image"``：將消息以圖片形式發送（不推薦）

* ``puid_logs`` *(str)* [預設：``null``]

  輸出 PUID 相關日誌到指定日誌路徑。請使用絕對路徑。PUID 日誌可能會根據對話數量和消息吞吐量而占用大量儲存空間。

* ``send_image_as_file`` *(bool)* [預設：``false``]

  以 JPEG 圖片方式發送自訂表情和 GIF，用於臨時繞過微信網頁版的自訂表情限制。詳見 `#48
  <https://ews.1a23.studio/issues/48>`_。

* ``system_chats_to_include`` *(list of str)** [預設: ``[filehelper]``]

  在預設對話列表中顯示的特殊系統對話。其內容僅能為
  ``filehelper``（文件傳輸助手）、``fmessage``（朋友推薦消息）、``newsapp``（騰訊新聞）、``weixin``（微信團隊）其中零到四個選項。

* ``user_agent`` *(str)* [預設值: ``null``]

  指定瀏覽網頁版微信時使用的使用者代理（user agent）字串。不指定時則使用 ``itchat`` 提供的預設值。

* ``text_post_processing`` *(bool)* [預設值：``true``]

  是否對從微信接收到的消息進行後處理。


供應商特定選項（``vendor_specific``）
=====================================

EWS 中的 ``Chat`` 提供了以下 ``vendor_specific`` 資料：

* ``is_mp`` *(bool)* 該對話是否為公眾號。

* ``is_contact`` *(bool)* 不明。提取自 API。

* ``is_blacklist_contact`` *(bool)* 該使用者是否被加入黑名單。

* ``is_conversation_contact`` *(bool)* 不明。提取自 API。

* ``is_room_contact_del`` *(bool)* 不明。提取自 API。

* ``is_room_owner`` *(bool)* 該使用者是否為群組建立者。

* ``is_brand_contact`` *(bool)* 不明。提取自 API。

* ``is_sp_contact`` *(bool)* 不明。提取自 API。

* ``is_shield_user`` *(bool)* 不明。提取自 API。

* ``is_muted`` *(bool)* 該對話是否在微信中開啟免打擾。

* ``is_top`` *(bool)* 該對話是否在微信中被置頂。

* ``has_photo_album`` *(bool)* 不明。提取自 API。


許可協議
========

EWS 使用了 `GNU Affero General Public License 3.0
<https://www.gnu.org/licenses/agpl-3.0.txt>`_ 或更新版本作為其開源許可:

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


翻譯支援
========

EWS 支援了介面本地化翻譯。您可以將語言環境變數（``LANGUAGE``、``LC_ALL``、``LC_MESSAGES`` 或
``LANG``）設為一種\ `已支援的語言
<https://crowdin.com/project/ehforwarderbot/>`_。同時，您也可以在我們的 `Crowdin
頁面 <https://crowdin.com/project/ehforwarderbot/>`_\ 裡將 EWS 翻譯為您的語言。

備註: 如果您使用原始碼安裝，您需要手動編譯翻譯字串文件（``.mo``）才可啟用翻譯後的介面。
