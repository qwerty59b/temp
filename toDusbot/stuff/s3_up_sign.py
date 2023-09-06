import json
import logging
import os
import re
import socket
import ssl
import sys
from base64 import b64decode, b64encode
from random import choice
from string import ascii_letters, digits

import aiofiles
import aiohttp
import xmltodict
from aiohttp import ClientSession


def send_data(so: ssl.SSLSocket, data: bytes):
    # print()
    # print(b'[SEND] ' + data)
    so.send(data)
    # time.sleep(1)


def analyze_answer(so: ssl.SSLSocket, sid, authstr, filesize, phone):
    m = so.recv().decode()
    # print('[RECEIVED] ' + m)
    # time.sleep(1)

    if m.startswith("<?xml version='1.0'?><stream:stream i='") and m.endswith(
        "v='1.0' xml:lang='en' xmlns:stream='x1' f='im.todus.cu' xmlns='jc'>"
    ):
        return analyze_answer(so, sid, authstr, filesize, phone)

    if (
        m
        == "<stream:features><es xmlns='x2'><e>PLAIN</e><e>X-OAUTH2</e></es><register xmlns='http://jabber.org/features/iq-register'/></stream:features>"
    ):
        send_data(so, b"<ah xmlns='ah:ns' e='PLAIN'>" + authstr + b"</ah>")
        return analyze_answer(so, sid, authstr, filesize, phone)

    if m == "<ok xmlns='x2'/>":
        send_data(
            so, b"<stream:stream xmlns='jc' o='im.todus.cu' xmlns:stream='x1' v='1.0'>"
        )
        return analyze_answer(so, sid, authstr, filesize, phone)

    if "<stream:features><b1 xmlns='x4'/>" in m:
        send_data(
            so, ("<iq i='" + sid + "-1' t='set'><b1 xmlns='x4'></b1></iq>").encode()
        )
        return analyze_answer(so, sid, authstr, filesize, phone)

    if "t='result' i='" + sid + "-1'>" in m:
        send_data(so, b"<en xmlns='x7' u='true' max='300'/>")
        send_data(
            so,
            (
                "<iq i='"
                + sid
                + "-3' t='get'><query xmlns='todus:purl' type='0' persistent='false' size='"
                + filesize
                + "' room=''></query></iq>"
            ).encode(),
        )
        return analyze_answer(so, sid, authstr, filesize, phone)

    if m.startswith("<ed u='true' max='"):
        send_data(so, ("<p i='" + sid + "-4'></p>").encode())
        return analyze_answer(so, sid, authstr, filesize, phone)

    if "t='result' i='" + sid + "-2'>" in m and "status='200'" in m:
        match = re.match(".*du='(.*)' stat.*", m)
        return match.group(1).replace("amp;", "") if match else None

    if m.startswith("<iq o='" + phone + "@im.todus.cu"):
        dict = xmltodict.parse("<root>" + m + "</root>")
        if dict:
            status = dict["root"]["iq"]["query"]["@status"]
            up_link = dict["root"]["iq"]["query"]["@put"].replace("amp;", "")
            down_link = dict["root"]["iq"]["query"]["@get"]
            if down_link:
                try:
                    down_link=down_link.split("?")[0]
                except:
                    logging.error("looks like it haves a rollback xdxd")

            return {"up": up_link, "down": down_link, "status": status}

    if "<not-authorized/>" in m:
        raise Exception("Error de autentificación")


def start_message_loop(so: ssl.SSLSocket, sid, authstr, url, phone):
    send_data(
        so, b"<stream:stream xmlns='jc' o='im.todus.cu' xmlns:stream='x1' v='1.0'>"
    )
    return analyze_answer(so, sid, authstr, url, phone)


def generate_session_id():
    return "".join(choice(ascii_letters + digits) for _ in range(5))


def get_signed_url(token: str, filepath: str):

    try:
        token_d = json.loads(b64decode(token.split(".")[1]).decode())
        phone = token_d["username"]

    except Exception as e:
        logging.error(f"TOKEN: {token}")
        logging.error(e)
        return None

    authstr = chr(0) + phone + chr(0) + token
    authstr = authstr.encode("utf-8")
    authstr = b64encode(authstr)

    sid = generate_session_id()

    host = "im.todus.cu"
    port = 1756

    try:

        filesize = os.path.getsize(filepath)

    except Exception as e:
        logging.error(e)
        return None

    sock = socket.socket(socket.AF_INET)
    sock.settimeout(10)

    wrappedSocket = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1_2)
    wrappedSocket.connect((host, port))

    try:
        return start_message_loop(wrappedSocket, sid, authstr, str(filesize), phone)

    except Exception as e:
        logging.error(e)
        return None


if __name__ == "__main__":
    try:
        token, filepath = sys.argv[1:]
    except:
        logging.error("Insuficientes parámetros")
        exit()

    print(get_signed_url(token, filepath))


async def read_in_chunks(filepath, chunk_size=1024, callback=None):
    total_size = os.path.getsize(filepath)
    async with aiofiles.open(filepath, "rb") as f:
        i = 1
        chunk = await f.read(chunk_size)
        while chunk:
            yield chunk
            if callback:
                i += 1
                await callback(min(i * chunk_size, total_size), total_size)
            chunk = await f.read(chunk_size)


async def upload_file_to_url(
    url: str, filepath: str, session: ClientSession, chunk_size=1024, callback=None
) -> aiohttp.ClientResponse:
    async with session.put(
        url=url, data=read_in_chunks(filepath, chunk_size, callback=callback)
    ) as resp:
        return resp
