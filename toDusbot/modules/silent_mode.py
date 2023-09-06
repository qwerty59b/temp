from telethon.events import NewMessage
from telethon.tl.custom import Button, Message

from toDusbot import bot, config
from toDusbot.modules.event_handlers import forbidden
from toDusbot.strings import reply_to_something_valid_you_dumb, select_file_size


@bot.on(NewMessage(pattern="/silent_mode"))
async def command_silent_mode(event: NewMessage.Event):
    if await forbidden(event):
        return

    args = [
        arg.strip()
        for arg in event.raw_text[12:]
        .replace(f"@{(await bot.get_me()).username}", "")
        .split()
    ]

    if not args or args[0] == "on":
        config["silent_mode"] = True

        await event.respond("Silent mode enabled")
    elif args[0] == "off":
        config["silent_mode"] = False

        await event.respond("Silent mode disabled")


@bot.on(NewMessage(pattern="/s3"))
async def command_esetre(event: NewMessage.Event):
    if await forbidden(event):
        return

    message: Message = await event.message.get_reply_message()

    if not message or not message.file or message.sticker or message.voice:
        await event.reply(reply_to_something_valid_you_dumb)
        return

    namaewa = message.file.name or (
        message.raw_text or "No_one_name" + message.file.ext
    )

    sizewas = round(message.file.size / 1024 / 1024, 3)
    await message.reply(
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
