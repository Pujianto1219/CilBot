# -*- coding: utf-8 -*-

"""

Helper sederhana untuk menyimpan & membangun konfigurasi API per plugin & per user.

Dipakai oleh plugin lain via: from ._perplugin_api import get_store, build_url, http_get_text, http_get_bytes

"""

import os

import io

import urllib.parse as urlparse

from urllib.request import urlopen, Request

USER_AGENT = "Mozilla/5.0 (PerPluginAPI-Helper)"

TIMEOUT = 20.0

MAX_TXT = 2 * 1024 * 1024      # 2 MB

MAX_BIN = 60 * 1024 * 1024     # 60 MB

def get_store(user_id: int, user_data: dict, plugin_key: str, defaults: dict) -> dict:

    u = user_data.setdefault(str(user_id), {})

    if not isinstance(u, dict):

        u = user_data[str(user_id)] = {}

    return u.setdefault(plugin_key, defaults.copy())

def ensure_dir(p: str):

    try: os.makedirs(p, exist_ok=True)

    except Exception: pass

def normalize_url(base: str, path_or_url: str) -> str:

    raw = (path_or_url or "").strip()

    if not raw: raise ValueError("Path/URL kosong.")

    if raw.startswith("http://") or raw.startswith("https://"):

        return raw

    if not raw.startswith("/"):

        raw = "/" + raw

    return base.rstrip("/") + raw

def build_url(base: str, path_or_url: str, extra_query: dict) -> str:

    """gabungkan base + path/url + query tambahan (tanpa overwrite query yang sudah ada)"""

    url = normalize_url(base, path_or_url)

    u = urlparse.urlparse(url)

    qs = dict(urlparse.parse_qsl(u.query, keep_blank_values=True))

    for k, v in (extra_query or {}).items():

        qs.setdefault(k, v)

    new_q = urlparse.urlencode(qs)

    return urlparse.urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))

def http_get_text(url: str) -> tuple[str, str]:

    req = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(req, timeout=TIMEOUT) as r:

        ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()

        raw = r.read(min(MAX_TXT, MAX_TXT))

        try: txt = raw.decode("utf-8", "replace")

        except Exception: txt = raw.decode("latin-1", "replace")

        return ctype, txt

def http_get_bytes(url: str) -> tuple[str, bytes]:

    req = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(req, timeout=TIMEOUT) as r:

        ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()

        buf = io.BytesIO()

        total = 0

        chunk = r.read(128 * 1024)

        while chunk:

            buf.write(chunk); total += len(chunk)

            if total > MAX_BIN: raise ValueError("Ukuran file melebihi batas (>%d MB)" % (MAX_BIN // (1024*1024)))

            chunk = r.read(128 * 1024)

        return ctype, buf.getvalue()