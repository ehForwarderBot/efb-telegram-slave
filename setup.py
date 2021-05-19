from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

__version__ = '0.1.0'

setup(
    name='efb-telegram-slave',
    version=__version__,
    description='Telegram Save Channel for EH Forwarder Bot, based on Telethon',
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    author='Sharzy L',
    author_email='me@sharzy.in',
    url='https://github.com/SharzyL/efb-telegram-slave',
    license='MIT',
    python_requires='>=3.8',
    install_requires=[
        'ehforwarderbot>=2.0.0',
        'telethon>=1.21',
        'PyYaml>=5.3',
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Communications :: Chat",
        "Topic :: Utilities"
    ],
    entry_points={
        'ehforwarderbot.slave': 'sharzy.telegram = efb_telegram_slave:TelegramChannel',
        'ehforwarderbot.wizard': 'sharzy.telegram = efb_telegram_slave.wizard:wizard'
    }
)

