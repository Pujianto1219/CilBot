# -*- coding: utf-8 -*-

"""

Notes Plugin (No-Duplicate Registration)

- Tidak memakai @client.on; pendaftaran handler dilakukan oleh controller dari nilai return run().

- Fitur:

  • .save <nama> <teks>   → simpan teks

  • (reply) .save <nama>  → simpan salinan pesan yang direply (media/teks) ke Saved Messages

  • #<nama>               → panggil note

  • .clear <nama>         → hapus note

  • .notes                → daftar note

Catatan:

- Data tersimpan di user_data[user_id]['notes'] dan akan diserialisasi oleh controller kamu (periodic save).

- Untuk konten media, plugin menyimpan salinan di Saved Messages (chat "me") dan mencatat saved_msg_id.

"""

import logging

from telethon import events

plugin_name = "Notes"

plugin_description = "Simpan & panggil notes: .save, #tag, .clear, .notes"

plugin_version = "1.0.0"

# ===== Helpers =====

def _notes_store(user_id_str: str, user_data: dict) -> dict:

    """Pastikan storage notes untuk user eksis & berbentuk dict."""

    u = user_data.setdefault(user_id_str, {})

    if not isinstance(u, dict):

        u = user_data[user_id_str] = {}

        logging.warning(f"[notes] user_data korup untuk {user_id_str}, direset.")

    return u.setdefault("notes", {})

async def _silent_delete(message):

    try:

        await message.delete()

    except Exception:

        pass

# ===== Handlers =====

async def _handle_save(event, client, user_data):

    """

    .save <nama> [teks]  (atau reply .save <nama> ke media/teks)

    """

    user_id_str = str(event.sender_id)

    notes = _notes_store(user_id_str, user_data)

    m = event.pattern_match

    name = (m.group(1) or "").strip().lower()

    rest = (m.group(2) or "").strip()

    if not name:

        return await event.edit("`Guna: .save <nama> <teks>` atau reply `.save <nama>` ke pesan.")

    reply = await event.get_reply_message()

    # Jika reply ada → simpan salinan pesan di Saved Messages

    if reply:

        await event.edit(f"`Menyimpan media/teks ke note #{name}...`")

        try:

            me_peer = await client.get_input_entity("me")

            saved_copy = await client.send_message(me_peer, reply)

            notes[name] = {"saved_msg_id": saved_copy.id, "kind": "message"}

            await event.edit(f"✅ Note `#{name}` disimpan (media/teks).")

        except Exception as e:

            logging.exception("[notes] save(reply) error")

            await event.edit(f"❌ Gagal simpan dari reply:\n`{e}`")

        return

    # Jika tidak reply → harus ada teks setelah nama

    if not rest:

        return await event.edit("`Guna: .save <nama> <teks>` atau reply `.save <nama>` ke pesan.")

    try:

        notes[name] = {"text": rest, "kind": "text"}

        await event.edit(f"✅ Note `#{name}` disimpan (teks).")

    except Exception as e:

        logging.exception("[notes] save(text) error")

        await event.edit(f"❌ Gagal simpan:\n`{e}`")

async def _handle_get(event, client, user_data):

    """

    #<nama> → kirim konten note.

    """

    user_id_str = str(event.sender_id)

    notes = _notes_store(user_id_str, user_data)

    name = (event.pattern_match.group(1) or "").strip().lower()

    if not name or name not in notes:

        # Diam jika tidak ada agar tidak spam

        return

    note = notes[name]

    # Simpan konteks reply_to sebelum trigger dihapus

    reply_to = event.reply_to_msg_id

    await _silent_delete(event)

    try:

        if note.get("kind") == "message" and "saved_msg_id" in note:

            me_peer = await client.get_input_entity("me")

            saved = await client.get_messages(me_peer, ids=note["saved_msg_id"])

            if saved:

                await client.send_message(event.chat_id, saved, reply_to=reply_to)

            else:

                await client.send_message(

                    event.chat_id,

                    f"❌ Salinan untuk `#{name}` hilang dari Saved Messages.",

                    reply_to=reply_to

                )

                # Rapikan agar error tidak berulang

                notes.pop(name, None)

        elif note.get("kind") == "text" and "text" in note:

            await client.send_message(event.chat_id, note["text"], reply_to=reply_to)

        else:

            await client.send_message(

                event.chat_id,

                f"❌ Note `#{name}` tidak valid.",

                reply_to=reply_to

            )

            notes.pop(name, None)

    except Exception as e:

        logging.exception("[notes] get error")

        await client.send_message(

            event.chat_id,

            f"❌ Gagal kirim `#{name}`:\n`{e}`",

            reply_to=reply_to

        )

async def _handle_clear(event, client, user_data):

    """

    .clear <nama> → hapus note (dan hapus salinan di Saved Messages jika ada).

    """

    user_id_str = str(event.sender_id)

    notes = _notes_store(user_id_str, user_data)

    name = (event.pattern_match.group(1) or "").strip().lower()

    if not name:

        return await event.edit("`Guna: .clear <nama>`")

    if name not in notes:

        return await event.edit(f"ℹ️ Note `#{name}` tidak ada.")

    info = notes.pop(name, {})

    # Coba hapus salinan di Saved Messages

    try:

        if info.get("kind") == "message" and "saved_msg_id" in info:

            me_peer = await client.get_input_entity("me")

            await client.delete_messages(me_peer, [info["saved_msg_id"]])

    except Exception:

        pass

    await event.edit(f"✅ Note `#{name}` dihapus.")

async def _handle_list(event, client, user_data):

    """

    .notes → daftar semua nama note.

    """

    user_id_str = str(event.sender_id)

    notes = _notes_store(user_id_str, user_data)

    if not notes:

        return await event.edit("`Belum ada note.`")

    names = sorted(notes.keys())

    text = "**Daftar Notes:**\n\n" + "\n".join(f"`#{n}`" for n in names)

    text += f"\n\nTotal: {len(names)}"

    await event.edit(text)

# ===== Entrypoint untuk Controller =====

async def run(client, user_id, user_data):

    """

    Dipanggil controller. Kembalikan list (handler, event_filter).

    Tidak ada dekorator -> tidak ada double registration.

    """

    return [

        (_wrap(_handle_save, client, user_data),

         events.NewMessage(pattern=r"^\.save(?:\s+([A-Za-z0-9_]+))(?:\s+(.*))?$", outgoing=True)),

        (_wrap(_handle_get, client, user_data),

         events.NewMessage(pattern=r"^#([A-Za-z0-9_]+)$", outgoing=True)),

        (_wrap(_handle_clear, client, user_data),

         events.NewMessage(pattern=r"^\.clear\s+([A-Za-z0-9_]+)$", outgoing=True)),

        (_wrap(_handle_list, client, user_data),

         events.NewMessage(pattern=r"^\.notes$", outgoing=True)),

    ]

# ===== Util pembungkus untuk inject client & user_data =====

def _wrap(func, client, user_data):

    async def _inner(event):

        return await func(event, client, user_data)

    return _inner