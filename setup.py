import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 6):
    raise Exception("Python 3.6 or higher is required. Your version is %s." % sys.version)

__version__ = ""
exec(open('efb_wechat_slave/__version__.py').read())

long_description = open('README.rst').read()

setup(
    name='efb-wechat-slave',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    version=__version__,
    description='WeChat Slave Channel for EH Forwarder Bot, based on WeChat Web API.',
    long_description=long_description,
    include_package_data=True,
    author='Eana Hufwe',
    author_email='ilove@1a23.com',
    url='https://github.com/blueset/efb-wechat-slave',
    license='AGPLv3+',
    python_requires='>=3.6',
    keywords=['ehforwarderbot', 'EH Forwarder Bot', 'EH Forwarder Bot Slave Channel',
              'wechat', 'weixin', 'chatbot'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Communications :: Chat",
        "Topic :: Utilities"
    ],
    install_requires=[
        "ehforwarderbot>=2.0.0b15",
        "itchat>=1.3.10",
        "python-magic",
        "pillow",
        "pyqrcode",
        "xmltodict",
        "PyYaml",
        "typing_extensions"
    ],
    entry_points={
        'ehforwarderbot.slave': 'blueset.wechat = efb_wechat_slave:WeChatChannel'
    }
)
