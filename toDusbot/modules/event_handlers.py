import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

import telethon
from telethon.events import CallbackQuery, ChatAction, NewMessage
from telethon.tl.custom import Button, Message
from telethon.tl.types import KeyboardButtonCallback, User

import toDusbot
from toDusbot import bot, bot_users, config, loop, stalker, groups
from toDusbot.strings import *
from toDusbot.stuff.bot_user import Queue, bot_user
from toDusbot.stuff.helper_functions import remaining_token_time
from toDusbot.stuff.upload_handlers import upload

try:
    import ujson as json
except:
    import json


boot_time = datetime.now()


async def forbidden(event: NewMessage.Event):
    not_possible = (int(event.chat_id) not in groups) and not (
        (int(event.chat_id) in bot_users) and not event.is_group
    )
    if not_possible and not event.is_group and stalker:
        message: Message = event.message
        await message.forward_to(groups[0])
    return not_possible


@bot.on(NewMessage())
async def file_handler(event: Union[NewMessage.Event, Message]):

    if await forbidden(event):
        return

    if not event.file or event.sticker or event.voice:
        return

    if event.is_group and config["silent_mode"]:
        return

    namaewa = event.file.name or (event.raw_text or "No_one_name" + event.file.ext)
    sizewas = round(event.file.size / 1024 / 1024, 3)
    await event.reply(
        select_file_size.format(namaewa, sizewas),
        buttons=[
            [
                Button.inline("1M", b"file_handler_1"),
                Button.inline("3M", b"file_handler_3"),
                Button.inline("5M", b"file_handler_5"),
            ],
            [
                Button.inline("10M", b"file_handler_10"),
                Button.inline("15M", b"file_handler_15"),
                Button.inline("20M", b"file_handler_20"),
            ],
            [
                Button.inline("30M", b"file_handler_30"),
                Button.inline("40M", b"file_handler_40"),
                Button.inline("50M", b"file_handler_50"),
            ],
            [Button.inline("Cancel", b"cancel")],
        ],
    )

@bot.on(NewMessage(pattern="/log"))
async def uploadLog(event: CallbackQuery.Event):
    if await forbidden(event):
        return

    await bot.send_file(event.chat_id, Path("").joinpath("toDus.log"))

@bot.on(CallbackQuery(data=re.compile(b"file_handler_")))
async def download_file(event: CallbackQuery.Event):
    if not toDusbot.token or remaining_token_time(toDusbot.token) <= 0:
        await event.answer(token_dialog, alert=True)
        return
    match = re.match(r"file_handler_(\d+)", event.data.decode())
    num = int(match.group(1))
    but_message: Message = await event.get_message()
    rep_message: Message = await but_message.get_reply_message()
    if event.is_group:
        user_id = rep_message.from_id.user_id
    else:
        user_id = rep_message.peer_id.user_id

    if num == 0:
        key = int(event.data.decode().split("=")[-1])
        bot_users[user_id].queue_dict[key].disable()
        bot_users[user_id].tasks[key].cancel()
        await event.answer()
        await but_message.edit(canceled_task, buttons=None)
        return
    task = loop.create_task(upload(rep_message, num))
    key = ""
    async with bot_users[user_id].tasksLock:
        key = max(bot_users[user_id].tasks.keys()) + 1

        bot_users[user_id].queue_dict[key] = Queue(
            rep_message.file.name or "Unnamed" + rep_message.file.ext,
            round(rep_message.file.size / 1024 / 1024, 3),
        )

        bot_users[user_id].tasks[key] = task
    await event.answer()
    but_message = await but_message.edit(
        cancel_task_dialog,
        buttons=[
            Button.inline(
                cancel_button_text, b"file_handler_0 key=" + str(key).encode()
            )
        ],
    )
    try:
        await task
        bot_users[user_id].queue_dict[key].disable()
        await but_message.delete()
    except asyncio.CancelledError:
        bot_users[user_id].queue_dict[key].disable()
        await but_message.delete()
    except Exception as exception_task:
        bot_users[user_id].queue_dict[key].disable()
        logging.error(exception_task)
        await but_message.delete()
        raise exception_task


@bot.on(CallbackQuery(data=b"cancel"))
async def cancel(event: CallbackQuery.Event):
    await event.delete()


@bot.on(ChatAction)
async def chat_action_handler(event: ChatAction.Event):
    if event.user_joined or event.user_added:
        users: List[User] = await event.get_users()
        for user in users:
            bot_users[user.id] = bot_user()
    if event.user_left or event.user_kicked:
        users: List[User] = await event.get_users()
        for user in users:
            bot_users.pop(user.id)


@bot.on(NewMessage(pattern="/uptime"))
async def uptime_handler(event):
    global boot_time
    now = datetime.now()
    delta = now - boot_time
    await bot.send_message(event.chat_id, f"Bot is up for {delta}")


@bot.on(NewMessage(pattern="/start"))
async def command_start(event: NewMessage.Event):
    if await forbidden(event):
        return

    await event.respond(start_message)


@bot.on(NewMessage(pattern="/queue"))
async def command_queue(event: NewMessage.Event):

    if await forbidden(event):
        return
    args = [
        arg.strip()
        for arg in event.raw_text[6:]
        .replace(f"@{(await bot.get_me()).username}", "")
        .split()
    ]

    if not args:

        def queue_dict_to_list(dictionary: Dict[int, Queue]):
            queue_list: List[str] = []
            counter = 0
            for queue_element in dictionary.values():
                if queue_element.enabled:
                    counter += 1
                    queue_list.insert(
                        counter,
                        queue_entry.format(
                            counter,
                            queue_element.file_name,
                            queue_element.file_size,
                        ),
                    )
            return queue_list

        status = queue_5
        if event.is_group:
            user_id = event.message.from_id.user_id
        else:
            user_id = event.message.peer_id.user_id
        cant = 0

        for values in bot_users[user_id].queue_dict.values():
            if values.enabled:
                cant += 1

        if cant > 10:
            status = queue_10
        if cant > 15:
            status = queue_15
        if cant == 0:
            await event.reply(queue_empty)
        else:
            real_queue = "\n".join(queue_dict_to_list(bot_users[user_id].queue_dict))
            await event.reply(queue_text.format(status, real_queue))

    if args[0] and args[0] == "g":

        text = ""

        for key in bot_users:

            user = bot_users[key]
            user_tasks, tasks_size = user.get_tasks()
            if user_tasks:
                user: User = (
                    await bot(telethon.functions.users.GetFullUserRequest(key))
                ).user
                text += (
                    global_queue_element.format(user.first_name, user_tasks, tasks_size)
                    + "\n"
                )

        await event.respond(
            global_queue_text.format(text) if text else global_queue_empty
        )


@bot.on(NewMessage(pattern="/token"))
async def command_token(event: NewMessage.Event):
    if await forbidden(event):
        return

    await bot.send_message(event.chat_id, f"`Bearer {toDusbot.token}`")


@bot.on(NewMessage(pattern="Bearer .+"))
async def command_Bearer(event: NewMessage.Event):
    if await forbidden(event):
        return

    _token = event.raw_text[7:].strip()

    if remaining_token_time(_token) <= 0:
        return

    toDusbot.token = _token
    toDusbot.headers["authorization"] = event.raw_text.strip()
    await event.respond(token_message)


@bot.on(NewMessage(pattern="/reset"))
async def command_reset(event: NewMessage.Event):
    if await forbidden(event):
        return

    users_count = 0
    tasks_count = 0

    for key in bot_users:
        user = bot_users[key]
        user_tasks, _ = user.get_tasks()
        if user_tasks:
            users_count += 1
            tasks_count += user_tasks

    await bot.send_message(
        event.chat_id,
        reset_pending_tasks_warning.format(users_count, tasks_count),
        buttons=[Button.inline(reset_button_button_text, b"reset_confirm")],
    )


@bot.on(CallbackQuery(data=b"reset_confirm"))
async def reset_confirm(event: CallbackQuery.Event):
    message: Message = await event.get_message()
    await message.edit(
        reset_button_header,
        buttons=[
            Button.inline("que siii", b"reset"),
            Button.inline("no", b"cancel"),
        ],
    )


@bot.on(CallbackQuery(data=b"reset"))
async def reset(event: CallbackQuery.Event):
    message: Message = await event.get_message()
    await message.edit(resetting, buttons=None)
    exit(333)


@bot.on(NewMessage(pattern="/options"))
async def command_options(event: NewMessage.Event):
    if await forbidden(event):
        return

    user_id = event.from_id.user_id if event.is_group else event.peer_id.user_id

    buttons: list[list[KeyboardButtonCallback]] = []

    for k, v in bot_users[user_id].options.items():
        buttons.append([Button.inline(f"{k}: {v}", f"option_{k}")])

    await event.reply(message="Options", buttons=buttons)


@bot.on(CallbackQuery(data=re.compile(b"option_")))
async def handle_option_callback(event: CallbackQuery.Event):
    match = re.match(r"option_(\w+)", event.data.decode())
    key = match.group(1)
    event_message: Message = await event.get_message()
    user_id = event.sender_id
    bot_users[user_id].options[key] ^= True

    buttons: list[list[KeyboardButtonCallback]] = []

    for k, v in bot_users[user_id].options.items():
        buttons.append([Button.inline(f"{k}: {v}", f"option_{k}")])

    await event_message.edit("Options", buttons=buttons)
