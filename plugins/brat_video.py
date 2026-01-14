# -*- coding: utf-8 -*-

"""

Brat Video Generator via Betabotz API

-------------------------------------

Menggunakan endpoint API https://api.betabotz.eu.org/api/maker/brat-video

untuk membuat video "brat" berdasarkan teks pengguna.

Perintah:

  .bratvideo <teks>

Catatan:

- API key disematkan langsung di plugin ini (per-plugin key).

- Tidak perlu .env, key dibaca langsung dari variabel KONSTAN di bawah.

- Jika respons API bukan video/mp4, akan ditampilkan pesan error singkat.

"""

import io

import logging

import urllib.parse

import asyncio

from telethon import events

plugin_name = "Brat Video"

plugin_description = "Generate video Brat dengan Betabotz API (per-plugin key)."

plugin_version = "1.0.1"

# ==== Konfigurasi API ====

API_BASE = "https://api.betabotz.eu.org"

API_KEY = "minatoaqua"  # << taruh API key di sini

ENDPOINT = "/api/maker/brat-video"

TIMEOUT = 30  # detik

MAX_SIZE = 60 * 1024 * 1024  # 60MB

USER_AGENT = "AcilBot-BratVideo/1.0"

# ==== Fungsi Util ====

async def fetch_video_bytes(session, url: str) -> bytes:

    """Unduh data video dari URL."""

    try:

        async with session.get(url, timeout=TIMEOUT) as resp:

            if resp.status != 200:

                text = await resp.text()

                raise ValueError(f"HTTP {resp.status}: {text[:200]}")

            content_type = resp.headers.get("Content-Type", "")

            if "video" not in content_type.lower():

                text = await resp.text()

                raise ValueError(f"Respons bukan video:\n{text[:200]}")

            data = await resp.read()

            if len(data) > MAX_SIZE:

                raise ValueError("Ukuran file melebihi batas 60MB.")

            return data

    except asyncio.TimeoutError:

        raise ValueError("Permintaan ke API timeout.")

    except Exception as e:

        raise ValueError(str(e))

# ==== Command Handler ====

async def bratvideo_command(event, client):

    """Menangani perintah .bratvideo"""

    text = (event.pattern_match.group(1) or "").strip()

    if not text:

        await event.edit("❌ Gunakan format: `.bratvideo <teks>`")

        return

    await event.edit("🎬 Membuat video brat, tunggu sebentar...")

    from aiohttp import ClientSession

    params = {

        "text": text,

        "apikey": API_KEY

    }

    query = urllib.parse.urlencode(params)

    full_url = f"{API_BASE.rstrip('/')}{ENDPOINT}?{query}"

    try:

        async with ClientSession(headers={"User-Agent": USER_AGENT}) as session:

            video_bytes = await fetch_video_bytes(session, full_url)

            # kirim hasilnya

            await event.delete()

            await client.send_file(

                event.chat_id,

                io.BytesIO(video_bytes),

                caption=f"🎞️ Brat Video\nTeks: {text}",

                file_name="brat_video.mp4"

            )

    except Exception as e:

        logging.error(f"[brat_video] Gagal: {e}")

        await event.edit(f"❌ Gagal membuat brat video:\n`{e}`")

# ==== Registrasi Plugin ====

async def run(client, user_id, user_data):

    """Daftarkan handler ke client"""

    return [

        (bratvideo_command, events.NewMessage(pattern=r"^\.bratvideo\s+(.+)$", outgoing=True))

    ]