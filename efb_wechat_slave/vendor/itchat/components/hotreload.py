import pickle
import os
import logging
import secrets

import requests

from ..config import VERSION
from ..returnvalues import ReturnValue
from ..storage import templates
from .contact import update_local_chatrooms, update_local_friends
from .messages import produce_msg

logger = logging.getLogger('itchat')


def load_hotreload(core):
    core.dump_login_status = dump_login_status
    core.load_login_status = load_login_status


def dump_login_status(self, fileDir=None):
    fileDir = fileDir or self.hotReloadDir
    status = {
        'version': VERSION,
        'loginInfo': self.loginInfo,
        'cookies': self.s.cookies.get_dict(),
        'storage': self.storageClass.dumps()}

    # Safe dump
    if not os.path.exists(fileDir):
        with open(fileDir, "wb") as f:
            pickle.dump(status, f)
    else:
        logger.debug("Attempting to overwrite session file.")
        temp_path = f"{fileDir}.{secrets.token_urlsafe(8)}"
        logger.debug(f"Write session file to {temp_path}.")
        with open(temp_path, "wb") as f:
            pickle.dump(status, f)
        logger.debug(f"Remove old session file at {fileDir}")
        os.unlink(fileDir)
        logger.debug(f"Move new session file from {temp_path} to {fileDir}")
        os.rename(temp_path, fileDir)
        logger.debug(f"Session file overwrite completed.")

    logger.debug('Dump login status for hot reload successfully.')


def load_login_status(self, fileDir,
                      loginCallback=None, exitCallback=None, recur=False):
    try:
        with open(fileDir, 'rb') as f:
            j = pickle.load(f)
    except (ImportError, ModuleNotFoundError) as e:
        # Mitigate the pickling issue of migrating itchat to ews.vendor.itchat
        if recur:
            raise e
        src = open(fileDir, 'rb').read()
        src = src.replace(b'citchat', b'cefb_wechat_slave.vendor.itchat')
        with open(fileDir, 'wb') as f:
            f.write(src)
        return self.load_login_status(fileDir, loginCallback, exitCallback, recur=True)
    except FileNotFoundError:
        logger.debug('No such file, loading login status failed.')
        return ReturnValue({'BaseResponse': {
            'ErrMsg': 'No such file, loading login status failed.',
            'Ret': -1002, }})

    if j.get('version', '') != VERSION:
        logger.debug(('you have updated itchat from %s to %s, ' +
                      'so cached status is ignored') % (
                         j.get('version', 'old version'), VERSION))
        return ReturnValue({'BaseResponse': {
            'ErrMsg': 'cached status ignored because of version',
            'Ret': -1005, }})
    self.loginInfo = j['loginInfo']
    if 'User' not in self.loginInfo:
        return ReturnValue({'BaseResponse': {
            'ErrMsg': 'Incomplete login info detected. Give up loading.',
            'Ret': -2000, }})
    self.loginInfo['User'] = templates.User(self.loginInfo['User'])
    self.loginInfo['User'].core = self
    self.s.cookies = requests.utils.cookiejar_from_dict(j['cookies'])
    self.storageClass.loads(j['storage'])
    try:
        msg_list, contact_list = self.get_msg()
    except:
        msg_list = contact_list = None
    try:
        sync_check_result = self.sync_check()
    except:
        sync_check_result = None
    if msg_list is None or contact_list is None or sync_check_result is None:
        self.logout()
        load_last_login_status(self.s, j['cookies'])
        logger.debug('server refused, loading login status failed.')
        return ReturnValue({'BaseResponse': {
            'ErrMsg': 'server refused, loading login status failed.',
            'Ret': -1003, }})
    else:
        if contact_list:
            for contact in contact_list:
                if '@@' in contact['UserName']:
                    update_local_chatrooms(self, [contact])
                else:
                    update_local_friends(self, [contact])
        if msg_list:
            msg_list = produce_msg(self, msg_list)
            for msg in msg_list: self.msgList.put(msg)
        self.start_receiving(exitCallback)
        logger.debug('loading login status succeeded.')
        if hasattr(loginCallback, '__call__'):
            loginCallback()
        return ReturnValue({'BaseResponse': {
            'ErrMsg': 'loading login status succeeded.',
            'Ret': 0, }})


def load_last_login_status(session, cookiesDict):
    try:
        session.cookies = requests.utils.cookiejar_from_dict({
            'webwxuvid': cookiesDict['webwxuvid'],
            'webwx_auth_ticket': cookiesDict['webwx_auth_ticket'],
            'login_frequency': '2',
            'last_wxuin': cookiesDict['wxuin'],
            'wxloadtime': cookiesDict['wxloadtime'] + '_expired',
            'wxpluginkey': cookiesDict['wxloadtime'],
            'wxuin': cookiesDict['wxuin'],
            'mm_lang': 'zh_CN',
            'MM_WX_NOTIFY_STATE': '1',
            'MM_WX_SOUND_STATE': '1', })
    except:
        logger.info('Load status for push login failed, we may have experienced a cookies change.')
        logger.info('If you are using the newest version of itchat, you may report a bug.')
