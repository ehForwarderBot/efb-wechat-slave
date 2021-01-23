import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 6):
    raise Exception("Python 3.6 or higher is required. Your version is %s." % sys.version)

__version__ = ""
exec(open('efb_wechat_slave/__version__.py').read())

long_description = open('README.rst').read()
tests_require = ["pytest", "mypy"]

setup(
    name='efb-wechat-slave',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    version=__version__,
    description='WeChat Slave Channel for EH Forwarder Bot, based on WeChat Web API.',
    long_description=long_description,
    include_package_data=True,
    author='Eana Hufwe',
    author_email='ilove@1a23.com',
    url='https://ews.1a23.studio',
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
        "ehforwarderbot>=2.0.0",
        "python-magic",
        "pillow",
        "pyqrcode",
        "pypng",
        "PyYaml>=5.3",
        "requests>=2.22.0",
        "typing_extensions",
        "bullet",
        "cjkwrap"
    ],
    extras_require={
        'tests': tests_require
    },
    tests_require=tests_require,
    entry_points={
        'ehforwarderbot.slave': 'blueset.wechat = efb_wechat_slave:WeChatChannel',
        'ehforwarderbot.wizard': 'blueset.wechat = efb_wechat_slave.wizard:wizard'
    }
)
