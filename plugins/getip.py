# -*- coding: utf-8 -*-

"""

Plugin .getip untuk ambil IP server (Betabotz)

Dipakai buat whitelist IP di https://api.betabotz.eu.org

"""

from telethon import events

from urllib.request import urlopen, Request

from urllib.error import URLError, HTTPError

plugin_name = "Get IP Betabotz"

plugin_description = "Ambil IP server untuk whitelist di Betabotz API."

plugin_version = "1.1.0"

# pakai API key kamu langsung di sini

API_KEY = "Btz-pCK9F"

USER_AGENT = "AcilBot-GetIP/1.0"

async def run(client, user_id, user_data):

    async def handle_getip(event):

        await event.edit("🔍 Mengambil IP server dari Betabotz...")

        try:

            url = f"https://api.betabotz.eu.org/ip?apikey={API_KEY}"

            req = Request(url, headers={"User-Agent": USER_AGENT})

            with urlopen(req, timeout=20) as resp:

                if resp.status != 200:

                    body = resp.read().decode("utf-8", "replace")

                    raise HTTPError(url, resp.status, body[:200], resp.headers, None)

                ip = resp.read().decode("utf-8", "replace").strip()

                if not ip:

                    await event.edit("❌ Gagal mengambil IP (respon kosong).")

                    return

            msg = (

                "🌐 **IP Server Kamu (Betabotz):**\n"

                f"`{ip}`\n\n"

                "**Langkah whitelist:**\n"

                "1. Buka web `https://api.betabotz.eu.org` dan login.\n"

                "2. Masuk ke **Profile → Settings → Management IP**.\n"

                "3. Tambahkan IP di atas ke whitelist.\n"

                "4. Simpan, lalu coba lagi fitur Mediafire / API lainnya."

            )

            await event.edit(msg)

        except (HTTPError, URLError) as e:

            await event.edit(f"❌ Gagal mengambil IP dari Betabotz:\n`{e}`")

        except Exception as e:

            await event.edit(f"❌ Error tidak diketahui:\n`{e}`")

    # daftar handler ke sistem plugin kamu

    return [

        (handle_getip, events.NewMessage(pattern=r"^\.getip$", outgoing=True)),

    ]