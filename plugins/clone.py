# -*- coding: utf-8 -*-

"""

Plugin Clone v1.3 (Revert Fix & Clean)

- Kloning profil target (nama, bio, foto), dan kembalikan (revert).

- FIX: .revert sekarang menghapus semua foto kloningan.

- FIX: .revert sekarang MENGEMBALIKAN bio/nama belakang KOSONG (jika aslinya kosong).

- FIX: Membersihkan semua spasi tersembunyi.

"""

import os

import logging

from telethon import events

from telethon.tl import functions, types

from telethon.tl.functions.users import GetFullUserRequest

from telethon.tl.functions.account import UpdateProfileRequest

# --- Konfigurasi Plugin ---

plugin_name = "Clone"

plugin_description = "Kloning profil (nama, bio, foto) target dan kembalikan lagi (.clone, .revert)"

plugin_version = "1.3.0" # Versi dinaikkan

# ===== Batas aman =====

MAX_FN = 64

MAX_LN = 64

MAX_ABOUT = 140 # Bio di Telethon/TG sekarang 140

def _ensure_dir(path: str):

    """Memastikan direktori ada."""

    try: os.makedirs(path, exist_ok=True)

    except Exception: pass

def _truncate(s: str | None, limit: int) -> str:

    """Memotong string jika melebihi batas (selalu return string)."""

    if not s: return "" # Kembalikan string kosong jika None

    s = str(s)

    return s if len(s) <= limit else s[:limit]

def _cache_folder_for(user_id: int) -> str:

    """Mendapatkan path folder cache unik per user."""

    p = os.path.join("cache", "clone", str(user_id)); _ensure_dir(p); return p

def _backup_slot(user_id: int) -> dict:

    """Membuat slot backup kosong."""

    return {"first_name": None, "last_name": None, "about": None, "photo_path": None, "had_photo": False, "ready": False}

def _get_backup_store(user_id_str: str, user_data: dict) -> dict:

    """Mengambil data backup dari user_data JSON."""

    u = user_data.setdefault(user_id_str, {})

    if not isinstance(u, dict): u = user_data[user_id_str] = {}; logging.warning(f"[clone] user_data korup u/{user_id_str}, reset.")

    if "clone_backup" not in u: u["clone_backup"] = _backup_slot(int(user_id_str))

    return u["clone_backup"]

async def _silent_edit(event, text):

    """Mengedit pesan dan mengabaikan error."""

    try: await event.edit(text)

    except Exception: pass

async def _resolve_target(event, client, arg: str | None):

    """Mencari target (dari reply atau argumen)."""

    if event.is_reply:

        msg = await event.get_reply_message()

        if msg and msg.sender_id: return await client.get_entity(msg.sender_id)

    if arg:

        try: return await client.get_entity(arg.strip())

        except Exception: return None

    return None

async def _download_current_user_photo(client, folder: str) -> tuple[bool, str | None]:

    """Download foto profil kita sendiri (sebelum kloning) untuk backup."""

    try:

        photos = await client.get_profile_photos("me", limit=1)

        if not photos: return False, None # Tidak punya foto

        path = os.path.join(folder, "backup_photo.jpg")

        await client.download_media(photos[0], file=path)

        return True, path # Punya foto, ini path-nya

    except Exception as e:

        logging.info(f"[clone] Tdk bisa download foto asli: {e}"); return False, None

async def _download_target_photo(client, target, folder: str) -> str | None:

    """Download foto profil target (yang akan dikloning)."""

    try:

        photos = await client.get_profile_photos(target, limit=1)

        if not photos: return None # Target tidak punya foto

        path = os.path.join(folder, "target_photo.jpg") # Default

        if hasattr(photos[0], 'video_sizes') and photos[0].video_sizes: path = os.path.join(folder, "target_photo.mp4") # Video profil

        await client.download_media(photos[0], file=path); return path

    except Exception as e:

        logging.info(f"[clone] Target tdk punya foto / fail download: {e}"); return None

def _photo_to_input(photo_obj):

    """Mengubah objek Photo menjadi InputPhoto untuk API delete."""

    if isinstance(photo_obj, types.Photo): return types.InputPhoto(id=photo_obj.id, access_hash=photo_obj.access_hash, file_reference=photo_obj.file_reference)

    return None

async def _delete_all_profile_photos(client):

    """Menghapus SEMUA foto profil yang sedang aktif."""

    try:

        photos = await client.get_profile_photos("me", limit=100)

        if not photos: return

        inputs = [p for p in (_photo_to_input(ph) for ph in photos) if p]

        if inputs: await client(functions.photos.DeletePhotosRequest(id=inputs)); logging.info(f"[clone] Hapus {len(inputs)} foto profil.")

    except Exception as e: logging.info(f"[clone] Gagal hapus foto: {e}")

# ===== Perintah Utama =====

async def _clone_command(event, client, user_data):

    """Handler untuk .clone"""

    user_id_str = str(event.sender_id); backup = _get_backup_store(user_id_str, user_data); args = (event.pattern_match.group(1) or "").strip() or None

    target = await _resolve_target(event, client, args)

    if not target or not isinstance(target, (types.User, types.Channel, types.Chat)): return await _silent_edit(event, "❌ Target tidak valid. Guna: `.clone <user>` atau reply.")

    try:

        if isinstance(target, types.User):

            full = await client(GetFullUserRequest(target.id)); target_about = getattr(full.full_user, "about", None); first_name = target.first_name or ""; last_name = target.last_name or "";

        else: first_name = target.title or "Cloned"; last_name = ""; full = await client(GetFullChatRequest(target.id)); target_about = getattr(full.full_chat, "about", None);

    except Exception as e: logging.exception("[clone] Gagal ambil profil target"); return await _silent_edit(event, f"❌ Gagal ambil profil target:\n`{e}`")

    folder = _cache_folder_for(int(user_id_str))

    if not backup.get("ready", False):

        await _silent_edit(event, "`Membuat backup profil asli...`")

        try:

            me_full = await client(GetFullUserRequest("me")); me_user = me_full.users[0] if me_full.users else (await client.get_me());

            backup["first_name"] = getattr(me_user, "first_name", "") or ""; backup["last_name"] = getattr(me_user, "last_name", "") or ""; backup["about"] = getattr(me_full.full_user, "about", None);

            had_photo, photo_path = await _download_current_user_photo(client, folder); backup["had_photo"] = had_photo; backup["photo_path"] = photo_path; backup["ready"] = True;

        except Exception as e: logging.exception("[clone] Gagal buat backup"); return await _silent_edit(event, f"❌ Gagal buat backup:\n`{e}`")

    await _silent_edit(event, "`Menyalin profil target...`")

    try:

        await client(UpdateProfileRequest(

            first_name=_truncate(first_name, MAX_FN) or " ", # Nama depan tdk boleh kosong

            last_name=_truncate(last_name, MAX_LN),

            about=_truncate(target_about, MAX_ABOUT)

        ))

    except Exception as e: logging.exception("[clone] Gagal update nama/bio"); return await _silent_edit(event, f"❌ Gagal ubah nama/bio:\n`{e}`")

    try:

        target_photo_path = await _download_target_photo(client, target, folder)

        if target_photo_path and os.path.exists(target_photo_path):

            file = await client.upload_file(target_photo_path)

            if target_photo_path.endswith(".mp4"): await client(functions.photos.UploadProfilePhotoRequest(video=file))

            else: await client(functions.photos.UploadProfilePhotoRequest(file=file))

        else: await _delete_all_profile_photos(client);

    except Exception as e: logging.info(f"[clone] Gagal set foto target: {e}")

    await _silent_edit(event, "✅ Profil berhasil dikloning.")

async def _revert_command(event, client, user_data):

    """Handler untuk .revert"""

    user_id_str = str(event.sender_id); backup = _get_backup_store(user_id_str, user_data)

    if not backup.get("ready", False): return await _silent_edit(event, "ℹ️ Belum ada backup. Jalankan `.clone` dulu.")

    await _silent_edit(event, "`Mengembalikan profil...`")

    

    # ==========================================================

    # --- PERBAIKAN LOGIKA REVERT BIO KOSONG ---

    # ==========================================================

    try:

        # Ambil nilai dari backup, default ke "" (string kosong) jika None

        revert_first = backup.get("first_name") or " " # Nama depan tdk boleh kosong

        revert_last = backup.get("last_name") or ""  # Default ke string kosong

        revert_bio = backup.get("about") or ""      # Default ke string kosong

        await client(UpdateProfileRequest(

            first_name=_truncate(revert_first, MAX_FN),

            last_name=_truncate(revert_last, MAX_LN),

            about=_truncate(revert_bio, MAX_ABOUT) # Kirim "" jika aslinya kosong

        ))

    except Exception as e:

        logging.exception("[clone] Gagal revert nama/bio")

        return await _silent_edit(event, f"❌ Gagal mengembalikan nama/bio:\n`{e}`")

    # ==========================================================

    # --- AKHIR PERBAIKAN ---

    # ==========================================================

    try:

        await _delete_all_profile_photos(client); logging.info("[clone] Foto kloningan dihapus.")

        if backup.get("had_photo"):

            photo_path = backup.get("photo_path")

            if photo_path and os.path.exists(photo_path): file = await client.upload_file(photo_path); await client(functions.photos.UploadProfilePhotoRequest(file=file)); logging.info("[clone] Foto asli dipulihkan.")

            else: logging.warning("[clone] Punya backup foto, tapi file path hilang.")

        # Jika had_photo=False, foto sudah bersih (dihapus di atas)

    except Exception as e: logging.info(f"[clone] Masalah saat revert foto: {e}")

    

    backup.clear(); backup.update(_backup_slot(int(user_id_str))); # Reset backup

    await _silent_edit(event, "✅ Profil dikembalikan. Backup dihapus.")

async def _help_command(event, *_):

    """Handler untuk .clone (tanpa argumen/reply)"""

    await _silent_edit(event, "**Clone Plugin (v1.3)**\n\n• `.clone <user>` → kloning.\n• `(reply) .clone` → kloning.\n• `.revert` → kembali asli.")

# --- Entrypoint ---

def _wrap(func, client, user_data):

    async def _inner(event): return await func(event, client, user_data)

    return _inner

async def run(client, user_id, user_data):

    """Fungsi 'run' dipanggil oleh ubot.py untuk mendaftarkan handler."""

    return [

        (_wrap(_clone_command, client, user_data), events.NewMessage(pattern=r"^\.clone(?:\s+(.+))?$", outgoing=True)),

        (_wrap(_revert_command, client, user_data), events.NewMessage(pattern=r"^\.revert$", outgoing=True)),

        (_wrap(_help_command, client, user_data), events.NewMessage(pattern=r"^\.clone$", outgoing=True)),

    ]