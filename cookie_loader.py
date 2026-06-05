"""
cookie_loader.py
────────────────
Netscape / Mozilla cookies.txt  →  dict  (for httpx / requests)

File format (each non-comment line):
  domain  flag  path  secure  expiry  name  value
"""

from pathlib import Path

COOKIE_FILE = Path(__file__).parent / "downloads" / "tera_cookies.txt"


def load_netscape_cookies(path: Path = COOKIE_FILE) -> dict:
    """
    Parse a Netscape-format cookies.txt file and return {name: value} dict.
    Lines starting with '#' (or blank) are skipped.
    """
    cookies: dict = {}
    if not path.exists():
        return cookies

    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.rstrip("\n")
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            # columns: domain, flag, path, secure, expiry, name, value
            name  = parts[5].strip()
            value = parts[6].strip()
            if name:
                cookies[name] = value

    return cookies


def load_cookie_string(path: Path = COOKIE_FILE) -> str:
    """Return cookies as a single 'name=value; name2=value2' string."""
    c = load_netscape_cookies(path)
    return "; ".join(f"{k}={v}" for k, v in c.items())


if __name__ == "__main__":
    # Quick test
    c = load_netscape_cookies()
    print(f"Loaded {len(c)} cookies:")
    for k, v in c.items():
        print(f"  {k} = {v[:30]}{'...' if len(v) > 30 else ''}")
