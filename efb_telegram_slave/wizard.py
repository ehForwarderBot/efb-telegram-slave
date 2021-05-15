import yaml
import asyncio
from pathlib import Path

from telethon.client import TelegramClient
import ehforwarderbot.utils as efb_utils
from . import TelegramChannel

def wizard(profile, instance_id):
    data = {}
    config_path = efb_utils.get_config_path(TelegramChannel.channel_id)
    if Path(config_path).exists():
        with config_path.open() as f:
            data = yaml.full_load(f)

    data['api_id'] = int(input("API id: "))
    data['api_hash'] = input("API hash: ")
    data['proxy'] = {}
    data['proxy']['protocol'] = input("Proxy protocol (http or socks5): ")
    data['proxy']['host'] = input("Proxy host: ")
    data['proxy']['port'] = int(input("Proxy port: "))

    loop = asyncio.get_event_loop()
    data_path = efb_utils.get_data_path(TelegramChannel.channel_id)
    proxy = (data['proxy']['protocol'], data['proxy']['host'], data['proxy']['port'])
    client = TelegramClient(f'{data_path}/{instance_id}',
                            data['api_id'],
                            data['api_hash'],
                            loop=loop,
                            proxy=proxy)
    client.start()
    print(data)
    with open(config_path, 'w') as f:
        yaml.dump(data, f)
