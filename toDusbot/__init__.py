import sys


import asyncio
import logging

logging.basicConfig(filename="toDus.log")

import os
from typing import Any, Dict

import telethon
from toDusbot.stuff.bot_user import bot_user

try:
    from dotenv import load_dotenv

    load_dotenv()
except:
    pass

api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
group_id = os.getenv("ADMIN")
groups=[]
todus_version = os.getenv("TODUS_VERSION", "1.3.29")
compilation_ver = os.getenv("COMPILATION_VERSION", "21858")
stalker = os.getenv("STALKER", True)
stalker = stalker and (stalker == "True")

for x in [api_id, api_hash, bot_token, group_id, todus_version, compilation_ver]:
    if not x:
        logging.error("Proper env variables need to be set")
        exit(0)

try:
    api_id = int(api_id)
    for i in group_id.split(","):
        groups.append(int(i))
except Exception as e:
    logging.error(e)
    exit(1)

socketLock = asyncio.Lock()
token = ""
bot_users: Dict[int, bot_user] = {}
config: Dict[Any, Any] = {"silent_mode": False}
loop = asyncio.get_event_loop()


headers = {
    "user-agent": f"ToDus {todus_version} HTTP-Upload",
    "authorization": "Bearer ",
    "accept-encoding": "gzip",
}

bot = telethon.TelegramClient("bot", api_id=api_id, api_hash=api_hash).start(
    bot_token=bot_token
)
print("Loaded env variables.")
