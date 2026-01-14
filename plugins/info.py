# -*- coding: utf-8 -*-

"""

Plugin Info v1.2

- FIX: Menangani kasus target tanpa foto profil (error 'Cannot use None as file').

- FEAT: Menampilkan foto profil target.

- FEAT: Menggunakan format output yang lebih sederhana.

"""

import os

from telethon import events

from telethon.tl.functions.users import GetFullUserRequest

from telethon.tl.functions.channels import GetFullChannelRequest

from telethon.tl.functions.messages import GetFullChatRequest

from telethon.utils import get_display_name

# --- Konfigurasi Plugin ---

plugin_name = "Info (dengan Foto)"

plugin_description = "Dapatkan info detail + foto user/grup/channel (.info <target>)"

plugin_version = "1.2" # Versi dinaikkan

# --- Fungsi Utama Plugin ---

async def run(client, user_id, user_data):

    """

    Fungsi 'run' ini dipanggil oleh ubot.py saat plugin dimuat.

    """

    @client.on(events.NewMessage(pattern=r"^\.info(?: |$)(.*)", outgoing=True))

    async def handle_info(event):

        """Menangani perintah .info"""

        target_entity = None

        args = event.pattern_match.group(1).strip()

        reply_msg = await event.get_reply_message()

        # Pesan tunggu (akan dihapus atau diedit)

        wait_msg = await event.edit("`Mengambil info...`")

        pfp_path = None # Path foto profil sementara

        try:

            # 1. Tentukan Target (Logika ini sudah benar)

            if reply_msg:

                try:

                    target_entity = await reply_msg.get_sender()

                    if not target_entity: target_entity = await reply_msg.get_chat()

                except Exception as e:

                    await wait_msg.edit(f"**Error:** Tidak dapat menemukan target dari balasan.\n`{e}`"); return

            elif args:

                try:

                    target_entity = await client.get_entity(args)

                except Exception as e:

                    await wait_msg.edit(f"**Error:** Tidak dapat menemukan target '{args}'.\n`{e}`"); return

            else:

                target_entity = await event.get_chat()

            if not target_entity:

                await wait_msg.edit("**Error:** Target tidak valid."); return

            # 2. Coba Unduh Foto Profil (Logika ini sudah benar)

            try:

                # Gunakan /tmp/ untuk Pterodactyl

                pfp_path = await client.download_profile_photo(

                    target_entity,

                    file=f"/tmp/info_pfp_{target_entity.id}.jpg", # Simpan di /tmp/

                    download_big=True

                )

            except Exception:

                pfp_path = None # Abaikan jika gagal

            # 3. Ambil dan Format Informasi Detail (Logika ini sudah benar)

            info_lines = []

            info_lines.append(f"**Nama:** `{get_display_name(target_entity)}`")

            info_lines.append(f"**ID:** `{target_entity.id}`")

            if hasattr(target_entity, 'username') and target_entity.username:

                info_lines.append(f"**Username:** @{target_entity.username}")

                info_lines.append(f"**Link:** https://t.me/{target_entity.username}")

            if hasattr(target_entity, 'first_name'):

                 info_lines.append(f"**Mention:** [{get_display_name(target_entity)}](tg://user?id={target_entity.id})")

            entity_type = "Tidak Diketahui"

            if hasattr(target_entity, 'bot') and target_entity.bot: entity_type = "Bot"

            elif hasattr(target_entity, 'first_name'): entity_type = "User"

            elif hasattr(target_entity, 'broadcast') and target_entity.broadcast: entity_type = "Channel"

            elif hasattr(target_entity, 'megagroup') and target_entity.megagroup: entity_type = "Supergroup"

            elif hasattr(target_entity, 'gigagroup') and target_entity.gigagroup: entity_type = "Gigagroup"

            elif hasattr(target_entity, 'participants_count'): entity_type = "Grup"

            info_lines.append(f"**Tipe:** `{entity_type}`")

            if entity_type == "User":

                try:

                    full_user = await client(GetFullUserRequest(target_entity.id))

                    if full_user.full_user.about: info_lines.append(f"**Bio:** `{full_user.full_user.about}`")

                    common_chats = full_user.full_user.common_chats_count

                    info_lines.append(f"**Grup Sama:** `{common_chats}`")

                except Exception: pass

            if "Grup" in entity_type:

                try:

                     full_chat = await client(GetFullChatRequest(target_entity.id))

                     info_lines.append(f"**Anggota:** `{full_chat.full_chat.participants_count}`")

                     if full_chat.full_chat.about: info_lines.append(f"**Deskripsi:** `{full_chat.full_chat.about}`")

                except Exception:

                     if hasattr(target_entity, 'participants_count'): info_lines.append(f"**Anggota:** `{target_entity.participants_count}`")

            if entity_type == "Channel":

                 try:

                     full_channel = await client(GetFullChannelRequest(target_entity.id))

                     if hasattr(full_channel.full_chat, 'participants_count'): info_lines.append(f"**Subscriber:** `{full_channel.full_chat.participants_count}`")

                     if full_channel.full_chat.about: info_lines.append(f"**Deskripsi:** `{full_channel.full_chat.about}`")

                 except Exception: pass

            if hasattr(target_entity, 'restricted') and target_entity.restricted:

                reasons = [f"- `{r.reason}` di `{r.platform}`" for r in target_entity.restriction_reason]

                info_lines.append("**Dibatasi:**\n" + "\n".join(reasons))

            if hasattr(target_entity, 'photo') and target_entity.photo:

                info_lines.append(f"**DC ID:** `{target_entity.photo.dc_id}`")

            info_text = "\n".join(info_lines)

            # ==========================================================

            # --- BAGIAN YANG DISESUAIKAN (PERBAIKAN ERROR) ---

            # ==========================================================

            # 4. Kirim Hasil (Logika Diperbaiki)

            if pfp_path and os.path.exists(pfp_path):

                # Jika ADA foto, kirim dengan foto

                await client.send_file(

                    event.chat_id,

                    file=pfp_path, # Kirim path file foto

                    caption=info_text,

                    link_preview=False,

                    reply_to=event.reply_to_msg_id or event.id

                )

                await wait_msg.delete() # Hapus pesan ".info" / "Mengambil info..."

            else:

                # Jika TIDAK ADA foto, edit pesan tunggu saja

                await wait_msg.edit(info_text, link_preview=False)

                # Tidak perlu hapus wait_msg karena sudah di-edit

            # ==========================================================

            # --- AKHIR PENYESUAIAN ---

            # ==========================================================

        except Exception as e:

            # Tampilkan error di pesan tunggu

            await wait_msg.edit(f"**Gagal mengambil info detail:**\n`{e}`")

        finally:

            # 5. Selalu hapus file foto jika ada (Logika ini sudah benar)

            if pfp_path and os.path.exists(pfp_path):

                try:

                    os.remove(pfp_path)

                except Exception as rm_err:

                     logging.error(f"Gagal hapus file temp info: {rm_err}")

    # Kembalikan daftar handler (tetap sama)

    return [

        (handle_info, events.NewMessage(pattern=r"^\.info(?: |$)(.*)", outgoing=True)),

    ]