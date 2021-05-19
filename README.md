# EFB Telegram Slave

[EH Forwarder Bot](https://github.com/ehForwarderBot) is an extensible message
tunneling chat bot framework.

It is sometimes useful if we have a Telegram slave channel for EFB. So there is
one, primarily based on [telethon](https://docs.telethon.dev). 

**Channel ID**: `sharzy.telegram`

## Installation

`pip3 install git+https://github.com/SharzyL/efb-telegram-slave`

To make EFB work, you need to configure some master channel and some slave
channels.  For complete usage guide, refer to [EFB user
guide](https://ehforwarderbot.readthedocs.io/en/latest/getting-started.html). 

## Configuration

Run `ehforwaderbot --profile <your-profile-name>` to run an interactive guide to 
complete the configuration. 

By default, configuration file is located in
`~/.ehforwarderbot/profiles/<your-profile-name>/sharzy.telegram/config.yaml`. 
Write the configuration following the following example. 

```yaml
# you should apply for a pair of api_hash and api_id in https://my.telegram.org/
api_hash: 12349061a3e1383920c2e05c1830a774
api_id: 1234567

# in case you need a proxy to access telegram
proxy: 
  protocol: http  # http / socks5 / socks4
  host: localhost
  port: 1234
```

## Features not supported yet

1. Rich text
2. Less used message types, such as Location 
3. Message edit and recall
4. Send sticker as .webp
5. Notification control

