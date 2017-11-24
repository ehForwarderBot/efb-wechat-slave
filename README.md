# EFB WeChat Slave Channel：EFB 微信从端 (EWS)
<!-- badges -->

![This project proudly supports #SayNoToWeChat campaign.](https://i.imgur.com/dCZfh14.png)

**Channel ID**: `ehforwarderbot.channels.slave.blueset.wechat`

EWS 是兼容 EH Forwarder Bot 的微信从端，基于逆向工程的微信网页版、
修改版 `wxpy`，`itchat`。

本项目的部分代码修改自 [youfou/wxpy](https://github.com/youfou/wxpy)。

## Alpha 版本
本项目目前仍是 Alpha 版本，仍不稳定，且功能可能随时变更。

## 使用前须知
自 2016 年中旬以来，陆续有用户报告其微信网页版登录被腾讯封禁。
表现为用任何方式登录微信网页版提示「当前登录环境异常。为了你的账号安全，
暂时不能登录 Web 微信。你可以通过手机客户端或 Windows 微信登录」
或类似的提示。只有不到半数的用户在封禁后通过各种方式恢复，但仍有相当数量的
用户还没有被解封。该封禁不影响其他客户端的登录。目前封禁的原因尚不明确。

如果你对网页版登录有要求的话，请慎用此 Channel。详细的相关信息请参见
项目 Wiki。

## 软件依赖
* Python >= 3.5
* EH Forwarder Bot >= 2.0.0
* ffmpeg
* libmagic
* pillow

## 可选的配置文件
EWS 支持使用可选的配置文件来启用实验功能。配置文件存储于 
`<当前配置文件夹>/ehforwarderbot.channels.slave.blueset.wechat/config.yaml`。 
当前配置文件夹的位置会根据用户的设定而改变。

__(EFB 2.0.0a1 中，默认的配置文件夹位于 `~/.ehforwarderbot/profiles`/defualt`)__

### 配置文件例

```yaml
# 实验功能
# 使用本段来调整实验功能的设置。请注意实验功能随时可能变更或失效。
# 详细说明见下文。
flags:
    option_one: 10
    option_two: false
    option_three: "foobar"
```

## 常见问题
* **如何切换已登录的微信账号？**  
  请登出当前的账号，并使用其他的微信手机登录。
* **如何登录两个微信账号？**  
  该功能没有正式支持，并需要使用者具有一定的技术能力。操作方法请参见项目 Wiki。
* **EWS 稳定吗？**  
  EWS 依赖于上游项目 [ItChat](https://github.com/littlecodersh/ItChat) 
  以及微信网页版的协议。根据 [ItChat FAQ](https://itchat.readthedocs.io/zh/latest/FAQ/)
  的说明，在满足以下情况的条件下，微信登录能够保持数个月稳定登录:
  * 服务器有稳定的网络连接，并且
  * **保持手机客户端长期在线。**


## 已知问题
TODO: 已知问题
<!--
* Random disconnection may occur occasionally due to the limit of protocol.
* Copyright protected sticker sets are not available to Web WeChat, leading to an empty sticker file to be delivered.
* Chat linking may be unstable sometime due to the limit of API.

**Technical detail**  
WeChat does not provide a stable chat identifier, so hash of the name of a user is used for the chat identifier. This may cause 2 issues:

* Chat is no longer traceable when its name is changed.
* Conflict and mis-delivery may happen when 2 users share the same name.
-->
## 实验功能
以下的实验功能可能不稳定，并可能随时更改、删除。使用时请注意。

* `refresh_friends` _(bool)_  [默认值: `false`]  
  每当请求会话列表时，强制刷新会话列表。
* `first_link_only` _(bool)_  [默认值: `false`]  
  在收到多链接消息时，仅发送第一条链接。默认多链接会发送多条消息。
* `max_quote_length` _(int)_  [默认值: `-1`]  
  引用消息中引文的长度限制。设置为 0 关闭引文功能。设置为 -1 则对引文长度
  不做限制。
* `qr_reload` _(str)_  [默认值: `"master_qr_code"`]  
  重新登录时使用的登录方式：  
  选项:
    * `"console_qr_code"`: 将二维码和提示输出到系统标准输出（`stdout`）。
    * `"master_qr_code"`: 将二维码和提示发送到主端。
  **注意**
  登录时二维码会频繁刷新，请注意二维码可能会导致刷屏。
* `on_log_out` _(str)_  [默认值: `"command"`]  
  微信服务器将用户登出时的操作。  
    选项:
    * `"idle"`: 仅通知用户。
    * `"reauth"`: 通知用户，并立即开始重新登录。
    * `"command"`: 通知用户，并等待用户启动重新登录过程。
* `imgcat_qr` _(bool)_  [默认值: `false`]  
  使用 [iTerm2 图像协议](https://www.iterm2.com/documentation-images.html)
  显示二维码。本功能只适用于 iTerm2 用户。
* `delete_on_edit` _(bool)_ [默认值: `false`]  
  以撤回并重新发送的方式代替编辑消息。默认禁止编辑消息。
  
## `vendor_specific`

EWS 的 `EFBChat` 提供了以下的 `vendor_specific` 项目：

* `is_mass_platform` _(bool)_  
  该会话是否为公众号。
* `wxpy_objet` _(wxpy.Chat)_  
  该会话所对应的 `wxpy.Chat` 对象。 