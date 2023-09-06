import asyncio
import logging
import os
import urllib.parse as urlparse
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Dict, List

import aiofiles
import aiohttp
from telethon.tl.custom import Message

import toDusbot
from toDusbot import bot, bot_users, socketLock
from toDusbot.exceptions import NotTokenExcept
from toDusbot.strings import *
from toDusbot.stuff.helper_functions import (
    get_files_md5sum,
    make_by_zip,
    order_links,
    progress_handler,
    upload_progress_handler,
)
from toDusbot.stuff.s3_up_sign import get_signed_url, upload_file_to_url


async def todus_upload(
    message: Message, filepath: Path, session: aiohttp.ClientSession, z7: bool, user_id
):
    """
    uploads a single file
    """

    filename = filepath.name

    async def get_signed(_token: str):
        a = get_signed_url(_token, filepath)
        if a is None or a["status"] != "200":
            for _ in range(10):
                a = get_signed_url(_token, filepath)
                if a is not None:
                    if a["status"] == "200":
                        toDusbot.token = _token
                        toDusbot.headers["authorization"] = f"Bearer {toDusbot.token}"
                        session.headers.update(toDusbot.headers)
                        return a
        else:
            return a
        raise NotTokenExcept()

    async with socketLock:
        urls: Dict[str, str] = await get_signed(toDusbot.token)
    if not urls:
        await bot.send_message(message.chat_id, get_upload_url_error.format(filename))
        return
    time_of_link = datetime.now()
    up_url = urls["up"]
    down_url = urls["down"]

    message = await message.edit(uploading_file.format(filename))
    response = None
    while True:
        try:
            response = await upload_file_to_url(
                up_url,
                filepath,
                session,
                chunk_size=1024,
                callback=partial(upload_progress_handler, message, filename),
            )
            if str(response.status).startswith("2"):
                break
            elif not str(response.status).startswith(
                "2"
            ) and datetime.now() - time_of_link > timedelta(minutes=2):
                break
        # except aiohttp.ClientOSError as exc:
        #     print(exc)
        #     await bot.send_message(message.chat_id, f'Error uploading \n{filename}\nConnection closed by toDus.')
        #     return
        # except asyncio.TimeoutError as exc:
        #     print(exc)
        #     await bot.send_message(message.chat_id, f'Error uploading \n{filename}\nTimeout Error.')
        #     return
        except Exception as exc:
            logging.error(exc)
        # await asyncio.sleep(10) #! ESTO LO ROMPE

    if not response:
        await bot.send_message(message.chat_id, not_response_error.format(filename))
        return

    if str(response.status).startswith("4") or str(response.status).startswith("5"):
        await bot.send_message(
            message.chat_id, upload_error.format(filename, response.status)
        )
        return
    message = await message.edit(file_uploaded.format(filename))

    if bot_users[user_id].options["verbose"] or z7:
        await bot.send_message(
            message.chat_id,
            f'[{os.path.splitext(filename)[0]}]({down_url + "?" + urlparse.quote(filename)})',
        )

    return down_url + "\t" + urlparse.unquote(filename)


async def upload(event: Message, part_size: int):
    """
    manages a complete upload task
    """
    user_id = event.from_id.user_id if event.is_group else event.peer_id.user_id

    async with bot_users[user_id].oneFileLock:

        if event.video and event.raw_text:
            filename: str = (
                event.raw_text.split("\n")[0].replace("/", "") + event.file.ext
            )
        else:
            filename: str = event.file.name

        if not filename:
            ext = event.file.ext
            if not ext:
                message: Message = await event.respond(file_has_no_name)
                return
            filename = (
                event.raw_text
                or ("Unnamed_" + str(int(datetime.now().timestamp()))) + ext
            )
        message: Message = await event.respond(downloading.format(filename))
        filepath = Path("./storage/", filename)

        if (
            filepath.exists()
            and filepath.is_file()
            and os.path.getsize(filepath) == event.file.size
        ):
            message = await message.edit(already_downloaded)
        else:
            c_exc = 3
            while c_exc > 0:
                try:
                    file = await event.download_media(
                        file=filepath,
                        progress_callback=partial(progress_handler, message, filename),
                    )
                    c_exc = 0
                except asyncio.CancelledError as exc:
                    raise exc
                except Exception as exc:
                    message = await message.edit(download_error)
                    c_exc -= 1
                    if c_exc == 0:
                        raise exc

            message = await message.edit(downloaded_message)

        path = filepath

        if os.path.getsize(path) <= part_size * 1024 * 1024:
            parts: List[Path] = [path]
            message = await message.edit(uploading)
        else:
            message = await message.edit(compressing)

            parts: List[Path] = list(sorted(Path(".").glob(str(path.stem) + ".7z*")))

            for part in parts:
                if part.name != path.name:
                    os.unlink(part)

            parts = await make_by_zip(path, part_size)
            message = await message.edit(uploading_x_parts.format(len(parts)))

        if sendMD5 := bot_users[user_id].options["checksum"]:
            md5sums = await get_files_md5sum(parts)
            md5file = Path("./storage", f"{path.stem}.md5")

            async with aiofiles.open(md5file, "w") as f:
                await f.write(md5sums)

        err_parts = []
        todus_urls = []
        intents = 0

        file_progress_message: Message = await bot.send_message(
            event.chat_id,
            file_upload_text,
        )

        while len(parts) > 0 and intents < 5:
            session = aiohttp.ClientSession(headers=toDusbot.headers)
            for part in parts:
                try:
                    url = await todus_upload(
                        file_progress_message,
                        part,
                        session,
                        len(parts) <= 1,
                        user_id,
                    )
                except NotTokenExcept:
                    await event.reply(not_token_exception_message)
                    return
                if url:
                    todus_urls.append(url)
                    await message.edit(
                        parts_uploaded_text.format(len(todus_urls), len(parts))
                    )
                if not url:
                    err_parts.append(part)
            parts = err_parts
            err_parts = []
            intents += 1
            await session.close()

        message = await event.respond(finish_response)

        if todus_urls:
            file_data = await order_links(todus_urls)
        txt_path = Path("./storage", f"{path.stem}.txt")

        async with aiofiles.open(txt_path, "w") as f:
            await f.write(file_data)

        txt_up_message = await event.respond(txt_up)

        txt_link = None
        retries = 0
        while retries < 5:
            session = aiohttp.ClientSession(headers=toDusbot.headers)
            txt_link = await todus_upload(
                txt_up_message, txt_path, session, False, user_id
            )
            if isinstance(txt_link, str):
                link, name = txt_link.split("\t")
                txt_link = f'{round(os.path.getsize(path) / 1024 / 1024, 3)} MB | [{os.path.splitext(name)[0]}]({link + "?" + urlparse.quote(name)})'
                break
            else:
                txt_link = None
            retries += 1
            await session.close()

        await bot.send_file(
            event.chat_id,
            ([txt_path, md5file] if sendMD5 else txt_path),
            caption=txt_link,
            reply_to=event.id,
        )

        if 10 >= len(parts) > 0 and part_size >= 5:
            await bot.send_message(
                event.chat_id, message=uploading_x_error_parts.format(len(parts))
            )
            for each in parts:
                await bot.send_file(event.chat_id, each)
