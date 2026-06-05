"""
terabox_api.py  —  TeraBox link resolver & file downloader.
"""

import re
import json
import asyncio
import time
import aiofiles
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx

from config import (
    API_DOMAINS, HEADERS, DOWNLOAD_DIR,
    get_cookies, get_cookie_string,
)

# ── 40 + domain regex ─────────────────────────────────────────────────────────

_TB_DOMAINS = (
    r"(?:(?:www\.)?terabox\.com"
    r"|(?:www\.)?terabox\.app"
    r"|dm\.terabox\.app"
    r"|(?:www\.)?teraboxapp\.com"
    r"|(?:www\.)?1024tera\.com"
    r"|(?:www\.)?1024terabox\.com"
    r"|(?:www\.)?freeterabox\.com"
    r"|(?:www\.)?4funbox\.com"
    r"|(?:www\.)?mirrobox\.com"
    r"|(?:www\.)?nephobox\.com"
    r"|(?:www\.)?tibibox\.com"
    r"|(?:www\.)?momerybox\.com"
    r"|(?:www\.)?bextbox\.com"
    r"|(?:www\.)?terabox\.link"
    r"|(?:www\.)?teraboxlink\.com"
    r"|(?:www\.)?terasharelink\.com"
    r"|(?:www\.)?terasharefile\.com"
    r"|(?:www\.)?terafileshare\.com"
    r"|(?:www\.)?terabox\.fun"
    r"|(?:www\.)?terabox\.cc"
    r"|(?:www\.)?terabox\.club"
    r"|(?:www\.)?teraboxdownload\.com"
    r"|(?:www\.)?teraboxvideo\.com"
    r"|(?:www\.)?diskwala\.com"
    r"|(?:www\.)?diskwala\.app"
    r"|(?:www\.)?teraboxshare\.com"
    r"|(?:www\.)?teraboxfiles\.com"
    r"|(?:www\.)?teraboxdl\.com"
    r"|(?:www\.)?teracloud\.com"
    r"|(?:www\.)?terabox\.xyz"
    r"|(?:www\.)?terabox\.me"
    r"|(?:www\.)?terabox\.net"
    r"|(?:www\.)?terabox\.org"
    r"|(?:www\.)?terabox\.io"
    r"|(?:www\.)?terabox\.co"
    r"|(?:www\.)?terabox\.in"
    r"|(?:www\.)?1024box\.com"
    r"|(?:www\.)?dubox\.com"
    r"|(?:www\.)?boxdrive\.com"
    r"|(?:www\.)?nutbox\.com"
    r"|(?:www\.)?fileterabox\.com"
    r"|(?:www\.)?terastorage\.com)"
)

TB_URL_REGEX = re.compile(
    rf"https?://{_TB_DOMAINS}"
    r"/(?:s/[a-zA-Z0-9_-]+|sharing/link\?(?:surl|shorturl)=[a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)


def find_tb_url(text: str) -> str | None:
    m = TB_URL_REGEX.search(text or "")
    return m.group(0) if m else None


def extract_surl(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        m = re.search(r"/s/([a-zA-Z0-9_-]+)", parsed.path)
        if m:
            return m.group(1)
        qs = parse_qs(parsed.query)
        for key in ("surl", "shorturl"):
            if key in qs:
                return qs[key][0]
    except Exception:
        pass
    return None


# ── TeraBoxAPI class ──────────────────────────────────────────────────────────

class TeraBoxAPI:

    def __init__(self):
        self._refresh()

    def _refresh(self):
        """Re-read cookies from file (called on each resolve so file changes take effect)."""
        self.cookies    = get_cookies()
        self.cookie_str = get_cookie_string()
        self.headers    = {**HEADERS, "Cookie": self.cookie_str} if self.cookie_str else {**HEADERS}

    # ── Low-level GET ─────────────────────────────────────────────────────────

    async def _get(self, url: str, params: dict = None) -> dict | None:
        try:
            async with httpx.AsyncClient(
                headers=self.headers, cookies=self.cookies,
                follow_redirects=True, timeout=20,
            ) as c:
                r = await c.get(url, params=params)
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
        return None

    # ── Page loader (for token extraction) ───────────────────────────────────

    async def load_page(self, surl: str) -> str:
        candidates = [
            f"https://www.1024tera.com/sharing/link?surl={surl}",
            f"https://www.terabox.com/sharing/link?surl={surl}",
            f"https://1024terabox.com/s/{surl}",
            f"https://terasharefile.com/s/{surl}",
        ]
        try:
            async with httpx.AsyncClient(
                headers=self.headers, cookies=self.cookies,
                follow_redirects=True, timeout=20,
            ) as c:
                for url in candidates:
                    try:
                        r = await c.get(url)
                        if r.status_code == 200 and len(r.text) > 200:
                            return r.text
                    except Exception:
                        continue
        except Exception:
            pass
        return ""

    def extract_tokens(self, html: str) -> dict:
        result = {"pcftoken": "", "bdstoken": "", "uk": ""}
        for key in ("pcftoken", "bdstoken"):
            m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', html)
            if m:
                result[key] = m.group(1)
        m = re.search(r'"uk"\s*:\s*(\d+)', html)
        if m:
            result["uk"] = m.group(1)
        m = re.search(r'var\s+templateData\s*=\s*(\{[\s\S]*?\})\s*;', html)
        if m:
            try:
                data = json.loads(m.group(1))
                result["pcftoken"] = data.get("pcftoken", result["pcftoken"])
                result["bdstoken"]  = data.get("bdstoken",  result["bdstoken"])
                result["uk"]        = str(data.get("uk",    result["uk"]))
            except Exception:
                pass
        return result

    # ── Share info & file list ────────────────────────────────────────────────

    async def get_shareinfo(self, surl: str) -> dict | None:
        params = {"shorturl": surl, "root": "1", "web": "1"}
        for domain in API_DOMAINS:
            data = await self._get(f"https://{domain}/api/shareinfo", params)
            if data and (data.get("sign") or data.get("errno") == 0):
                return data
        return None

    async def get_file_list(self, surl: str, path: str = "/") -> list:
        params = {
            "shorturl": surl,
            "root":     "1" if path == "/" else "0",
            "web":      "1",
            "page":     "1",
            "num":      "100",
            "dir":      path,
        }
        for domain in API_DOMAINS:
            data = await self._get(f"https://{domain}/share/list", params)
            if data and data.get("errno") == 0 and data.get("list"):
                return data["list"]
        return []

    async def get_folder_files_recursive(self, surl: str, path: str = "/") -> list:
        items = await self.get_file_list(surl, path)
        all_files = []
        for item in items:
            if int(item.get("isdir", 0)):
                sub_path = item.get("path", f"{path}/{item.get('server_filename','')}")
                sub_files = await self.get_folder_files_recursive(surl, sub_path)
                all_files.extend(sub_files)
            else:
                all_files.append(item)
        return all_files

    # ── Download link ─────────────────────────────────────────────────────────

    async def get_download_link(
        self, fs_id: str, shareinfo: dict, pcftoken: str
    ) -> str | None:
        sign      = shareinfo.get("sign", "")
        timestamp = str(shareinfo.get("timestamp", ""))
        uk        = str(shareinfo.get("uk", ""))
        share_id  = str(shareinfo.get("shareid", ""))

        if not sign or not timestamp:
            return None

        params = {
            "app_id":     "250528",
            "web":        "1",
            "channel":    "dubox",
            "clienttype": "0",
            "sign":       sign,
            "timestamp":  timestamp,
            "uk":         uk,
            "shareid":    share_id,
            "primaryid":  share_id,
            "fidlist":    json.dumps([int(fs_id)]),
        }

        cookie_str = self.cookie_str
        if pcftoken and f"pcftoken={pcftoken}" not in cookie_str:
            cookie_str += f"; pcftoken={pcftoken}"

        headers = {**self.headers, "Cookie": cookie_str}

        try:
            async with httpx.AsyncClient(
                headers=headers, follow_redirects=True, timeout=20,
            ) as c:
                for domain in API_DOMAINS:
                    try:
                        r = await c.get(
                            f"https://{domain}/api/download", params=params
                        )
                        if r.status_code != 200:
                            continue
                        data = r.json()
                        if data.get("errno") == 0:
                            dlink = data.get("dlink", [])
                            if isinstance(dlink, list) and dlink:
                                return dlink[0]
                            if isinstance(dlink, str) and dlink:
                                return dlink
                        elif data.get("errno") == -6:
                            return None
                    except Exception:
                        continue
        except Exception:
            pass
        return None

    # ── Main resolver ─────────────────────────────────────────────────────────

    async def resolve(self, url: str) -> dict | None:
        self._refresh()   # reload cookies from file on every resolve

        surl = extract_surl(url)
        if not surl:
            return None

        html, shareinfo, raw_top = await asyncio.gather(
            self.load_page(surl),
            self.get_shareinfo(surl),
            self.get_file_list(surl, "/"),
        )

        if not shareinfo or not raw_top:
            return None

        tokens   = self.extract_tokens(html)
        pcftoken = (
            tokens.get("pcftoken")
            or self.cookies.get("pcftoken", "")
            or self.cookies.get("csrfToken", "")
        )

        # Expand root-level folders recursively
        all_raw = []
        for item in raw_top:
            if int(item.get("isdir", 0)):
                sub_path = item.get("path", f"/{item.get('server_filename','')}")
                sub = await self.get_folder_files_recursive(surl, sub_path)
                all_raw.extend(sub)
            else:
                all_raw.append(item)

        files = [
            {
                "filename": f.get("server_filename") or f.get("filename", "file"),
                "size":     int(f.get("size", 0)),
                "fs_id":    str(f.get("fs_id", "")),
                "is_dir":   int(f.get("isdir", 0)),
                "dlink":    f.get("dlink", ""),
                "md5":      f.get("md5", ""),
                "thumb":    (f.get("thumbs") or {}).get("url3", ""),
            }
            for f in all_raw
        ]

        return {
            "surl":      surl,
            "files":     files,
            "shareinfo": shareinfo,
            "pcftoken":  pcftoken,
        }


# ── File downloader ───────────────────────────────────────────────────────────

def sanitize(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)


async def download_file(
    dlink: str,
    filename: str,
    size: int,
    cookies: dict,
    cookie_str: str,
    progress_cb=None,
) -> Path | None:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = DOWNLOAD_DIR / sanitize(filename)

    existing = save_path.stat().st_size if save_path.exists() else 0
    if existing and size and existing == size:
        return save_path   # already fully downloaded

    headers = {**HEADERS}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    if cookie_str:
        headers["Cookie"] = cookie_str

    try:
        async with httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=httpx.Timeout(60, read=600),
        ) as c:
            async with c.stream("GET", dlink) as r:
                if r.status_code not in (200, 206):
                    return None

                total = int(r.headers.get("content-length", 0)) + existing
                if not total and size:
                    total = size

                mode = "ab" if existing else "wb"
                done = existing

                async with aiofiles.open(save_path, mode) as fh:
                    async for chunk in r.aiter_bytes(1024 * 1024):
                        await fh.write(chunk)
                        done += len(chunk)
                        if progress_cb and total:
                            await progress_cb(done, total)
        return save_path
    except Exception:
        return None
