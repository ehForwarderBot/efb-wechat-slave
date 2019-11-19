import os
import platform

VERSION = '1.3.10.post2'
BASE_URL = 'https://login.weixin.qq.com'
OS = platform.system()  # Windows, Linux, Darwin
DIR = os.getcwd()
DEFAULT_QR = 'QR.png'
TIMEOUT = (10, 60)
