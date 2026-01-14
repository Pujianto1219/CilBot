# -*- coding: utf-8 -*-

"""

Mediafire Downloader (Betabotz API) untuk Bot Controller

--------------------------------------------------------

Dipakai oleh controller melalui:

  - can_handle(url)  -> cek apakah plugin ini bisa menangani URL

  - handle_url(event, url) -> proses download & kirim file

Endpoint API:

  https://api.betabotz.eu.org/api/download/mediafire?url=<link>&apikey=<key>

"""

import asyncio

import json

import logging

from urllib.parse import quote_plus

from urllib.request import urlopen, Request

from urllib.error import URLError, HTTPError

plugin_name = "Mediafire Downloader"

plugin_description = "Unduh file Mediafire via Betabotz API."

plugin_version = "1.0.0"

# === KONFIG API PER PLUGIN ===

API_BASE = "https://api.betabotz.eu.org/api/download/mediafire"

API_KEY  = "Btz-pCK9F"  # <-- TARUH API KEY DI SINI

USER_AGENT = "AcilBot-Mediafire/1.0"

TIMEOUT    = 40  # detik

# ===== Util: HTTP GET JSON sinkron (dibungkus executor) =====

def _http_get_json(url: str) -> dict:

    """Request sinkron → JSON dict (jalan di thread terpisah dari event loop)."""

    req = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(req, timeout=TIMEOUT) as resp:

        if resp.status != 200:

            body = resp.read()

            try:

                text = body.decode("utf-8", "replace")

            except Exception:

                text = str(body)

            raise RuntimeError(f"HTTP {resp.status} {resp.reason}: {text[:200]}")

        raw = resp.read()

        try:

            return json.loads(raw.decode("utf-8", "replace"))

        except Exception as e:

            raise RuntimeError(f"Gagal parse JSON: {e}")

async def _fetch_json(url: str) -> dict:

    """Wrapper async untuk _http_get_json."""

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(None, _http_get_json, url)

# ===== API utk controller: deteksi URL =====

def can_handle(url: str) -> bool:

    """Kembalikan True jika URL adalah link Mediafire."""

    if not isinstance(url, str):

        return False

    return "mediafire.com" in url.lower()

# ===== API utk controller: proses URL =====

async def handle_url(event, url: str):

    """

    Dipanggil oleh controller saat user kirim link & status waiting_download_link.

    - event: Telethon NewMessage event dari BOT

    - url:   link Mediafire

    """

    chat_id = event.chat_id

    reply_to = event.id

    # info awal ke user

    try:

        await event.respond("📦 Mengambil data Mediafire... Mohon tunggu.")

    except Exception:

        pass

    # build URL API

    q = quote_plus(url)

    api_url = f"{API_BASE}?url={q}&apikey={API_KEY}"

    try:

        data = await _fetch_json(api_url)

        if not isinstance(data, dict) or "result" not in data:

            raise RuntimeError("Respon API tidak valid (result tidak ditemukan).")

        res = data["result"]

        file_url   = res.get("url")

        filename   = res.get("filename", "mediafire_file")

        ext        = res.get("ext", "bin")

        upload_dt  = res.get("upload_date", "Unknown")

        size_human = res.get("filesizeH", res.get("filesize", "Unknown"))

        caption = (

            f"**💌 Name:** `{filename}`\n"

            f"**📊 Size:** `{size_human}`\n"

            f"**🗂️ Extension:** `{ext}`\n"

            f"**📨 Uploaded:** `{upload_dt}`"

        )

        # kirim info

        await event.respond(caption)

        if not file_url:

            raise RuntimeError("URL file kosong di respon API.")

        # kirim file sebagai dokumen

        await event.client.send_file(

            chat_id,

            file=file_url,

            caption=f"{filename}\n\n_Download via Betabotz_",

            force_document=True,

            reply_to=reply_to

        )

    except (HTTPError, URLError) as e:

        logging.error(f"[mediafire] HTTP error: {e}")

        try:

            await event.respond(f"❌ Gagal menghubungi API Mediafire:\n`{e}`")

        except Exception:

            pass

    except Exception as e:

        logging.error(f"[mediafire] Error: {e}")

        try:

            await event.respond(f"❌ Terjadi kesalahan saat memproses link Mediafire:\n`{e}`")

        except Exception:

            pass