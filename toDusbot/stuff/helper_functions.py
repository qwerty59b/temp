import asyncio
import base64
import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import aiofiles
from telethon.tl.custom import Message

import toDusbot
from toDusbot.strings import *

try:
    import ujson as json
except:
    import json

import time

import multivolumefile
import py7zr
from py7zr import FILTER_COPY


def slow(secs):
    def dec(f):
        t = {"last_update": datetime.now(timezone.utc)}

        async def wrapper(*args, **kwargs):
            now = datetime.now(timezone.utc)
            if now - t["last_update"] < timedelta(seconds=secs):
                return
            t["last_update"] = now
            return await f(*args, **kwargs)

        return wrapper

    return dec


@slow(2)
async def progress_handler(
    message: Message, filename: str, received_bytes, total_bytes
):
    try:
        await message.edit(
            download_progress.format(
                filename, round(int(received_bytes) * 100 / int(total_bytes), 2)
            )
        )
    except asyncio.CancelledError as exc:
        raise exc
    except Exception as exc:
        logging.error(exc)


@slow(2)
async def upload_progress_handler(
    message: Message, filename: str, received_bytes, total_bytes
):
    try:
        await message.edit(
            upload_progress.format(
                filename, round(int(received_bytes) * 100 / int(total_bytes), 2)
            )
        )
    except asyncio.CancelledError as exc:
        raise exc
    except Exception as exc:
        logging.warn(exc)


async def make_by_zip(path: Path, part_size: int):
    copy_filter = [{"id": FILTER_COPY}]

    ticket = str(time.strftime("%Y-%m-%d-%H-%M-%S"))
    partsdir = path.parent / ticket

    try:
        os.mkdir(partsdir)
    except Exception as _:
        pass

    filename_7z = path.name + ".7z"

    with multivolumefile.open(
        partsdir / filename_7z, "wb", part_size * 1024 * 1024
    ) as target_archive:
        with py7zr.SevenZipFile(target_archive, "w", filters=copy_filter) as archive:
            archive.writeall(path, path.name)

    # Fix for the 4 figures
    parts_raw = list(Path(partsdir).glob("*"))
    for part in parts_raw:
        part_parent_psx = part.parent.as_posix()
        part_sfx = part.suffix[2:]
        part.rename(Path(part_parent_psx + "/" + part.stem + "." + part_sfx))

    return list(Path(partsdir).glob("*"))


async def order_links(todus_urls: List[str]):
    """
    returns the ordered links as text in txt ready format\n

    `link1[tab]name1`\n
    `link2[tab]name2`\n

    """
    dictionary = {}
    for item in todus_urls:
        v = item.split("\t")
        if len(v) == 2:
            dictionary[v[1]] = v[0]

    keys = sorted(dictionary.keys())
    return "".join(f"{dictionary[key]}\t{key}\n" for key in keys)


async def get_files_md5sum(paths: List[Path]) -> str:
    file_content = ""

    for path in paths:
        file_hash = hashlib.md5()
        async with aiofiles.open(path, "rb") as f:
            while chunk := await f.read(8192):
                file_hash.update(chunk)
        file_content += f"{file_hash.hexdigest()} ./{path.name}\n"

    return file_content


def remaining_token_time(token):
    if not token or ".ey" not in token:
        return 0
    try:
        info = json.loads(
            base64.decodebytes(token.split(".")[1].encode("utf-8")).decode("utf-8")
        )
        return int(info["exp"]) - int(datetime.now().timestamp())
    except Exception as e:
        logging.error(e)
        return 0
