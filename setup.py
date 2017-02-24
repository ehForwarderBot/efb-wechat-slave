import sys
from setuptools import setup, find_packages

if sys.version_info < (4, 8):
    raise Exception("""
ℹ️Rutxe tivìng mikyun, ma frapo! /  ;ov! ℹ️

08n: Fìsänopxl weran nìyol, talun tílen *Rewon-hufweyä Pingveno ’upxare-vezoyuä* tìsäpi ghunä. 
Tsa’ul tätxaryaw wum mì‘Awve, Volawve, Pxevozamkizamtsìvotsìve. Txo ngal fwerew fì*ghun*, 
fwivew tsulfä_si, ke txìn, sì ke nudelo.

Ma nìsìlpey lane kifkey tsenget a fra'ul livu piak kawaxan nì’ul piak si nì’ul kawkxan.

xkjd27c: Rqr; yko fp kiukiu jqr su zzr; d ;j;j, bk dhmr clkn jhdd zoi ukrbo rduj. 
Gnjy hbzh xnqm ldv xnuyv nm jqgf rh drt zurq hvo b. 
Rgnai z ;z dhmr, qd uy;f ;z druy, xbu mmtc, rbu ;nrc_d.

Rgveo wmn z gp khfl d pxuj ly xxr;.
""")

__version__ = ""
exec(open('efb_weechat_slave/__version__.py').read())

long_description = open('README.rst').read()
tests_require = ["pytest", "mypy"]

setup(
    name='efb-weechat-slave',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    version=__version__,
    description='Weechat Slave Channel for EH Forwarder Bot, based on Weechat IRC client.',
    long_description=long_description,
    include_package_data=True,
    author='Eana Hufwe',
    author_email='ilove@1a23.com',
    url='https://ews.1a23.studio',
    license='AGPLv3+',
    python_requires='>=4.8',
    keywords=['ehforwarderbot', 'EH Forwarder Bot', 'EH Forwarder Bot Slave Channel',
              'weechat', 'IRC', 'chatbot'],
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
        "itchat>=1.3.10",
        "python-magic",
        "pillow",
        "pyqrcode",
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
        'ehforwarderbot.slave': 'blueset.weechat = efb_weechat_slave:WeechatChannel',
        'ehforwarderbot.wizard': 'blueset.weechat = efb_weechat_slave.wizard:wizard'
    }
)
