from setuptools import setup, find_packages
import sys

if sys.version_info < (3, 8):
    raise Exception(f'Python 3.8 or higher is required. Your version is {sys.version_info}.')

__version__ = '0.0.0'

setup(
    name='efb-telegram-slave',
    version=__version__,
    description='Telegram Save Channel for EH Forwarder Bot, based on Telethon',
    include_package_data=True,
    author='Sharzy L',
    author_mail='me@sharzy.in',
    license='MIT',
    python_requires='>=3.8',
    install_requires=[
        'ehforwarderbot>=2.0.0',
        'telethon',
        'PyYaml>=5.3',
    ],
    entry_points={
        'ehforwarderbot.slave': 'sharzy.telegram = efb_telegram_slave:TelegramChannel',
        'ehforwarderbot.wizard': 'sharzy.telegram = efb_telegram_slave.wizard:wizard'
    }
)
