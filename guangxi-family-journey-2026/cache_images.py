from __future__ import annotations

import hashlib
import html as html_lib
import mimetypes
import re
import shutil
import sys
import urllib.request
from pathlib import Path

SRC = Path("guangxi-family-journey-2026/index.html")
OUT = Path("_site")
ASSETS = OUT / "assets"

text = SRC.read_text(encoding="utf-8")
OUT.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)

# Match the Wikimedia URLs currently used by the site.
urls = list(dict.fromkeys(re.findall(
    r'src="(https://commons\.wikimedia\.org/wiki/Special:Redirect/file/[^"]+)"',
    text,
)))

fallback = ASSETS / "fallback.svg"
fallback.write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#dbe9df"/><stop offset="1" stop-color="#8fb3a6"/></linearGradient></defs>
<rect width="1200" height="800" fill="url(#g)"/><path d="M0 620L280 340l170 170 180-250 190 210 160-130 220 280v180H0z" fill="#315e53" opacity=".7"/><circle cx="930" cy="180" r="78" fill="#f3d39a"/><text x="600" y="720" text-anchor="middle" font-size="42" fill="#f8fbf9" font-family="sans-serif">广西 · 山水到海</text></svg>''', encoding="utf-8")

ok = 0
failed: list[tuple[str, str]] = []
for i, raw_url in enumerate(urls, start=1):
    url = html_lib.unescape(raw_url)
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; GuangxiJourneyPages/1.0; +https://github.com/peoplea/notes)",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            ctype = (r.headers.get_content_type() or "").lower()
            if not ctype.startswith("image/"):
                raise RuntimeError(f"unexpected content-type {ctype}")
            ext = mimetypes.guess_extension(ctype) or ".jpg"
            if ext == ".jpe":
                ext = ".jpg"
            dest = ASSETS / f"travel-{i:02d}-{digest}{ext}"
            dest.write_bytes(data)
            text = text.replace(raw_url, f"assets/{dest.name}")
            ok += 1
            print(f"OK {i:02d}: {ctype} {len(data)} bytes -> {dest.name}")
    except Exception as e:
        text = text.replace(raw_url, "assets/fallback.svg")
        failed.append((url, repr(e)))
        print(f"FAILED {i:02d}: {url} :: {e}", file=sys.stderr)

(OUT / "index.html").write_text(text, encoding="utf-8")

print(f"Cached {ok}/{len(urls)} unique remote images locally.")
if failed:
    print("Failed URLs were replaced by a local fallback so the page never shows a broken-image icon.", file=sys.stderr)
    for url, err in failed:
        print(f" - {url} :: {err}", file=sys.stderr)
