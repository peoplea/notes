from __future__ import annotations

import concurrent.futures
import hashlib
import html as html_lib
import mimetypes
import re
import sys
import urllib.request
from pathlib import Path

SRC = Path("guangxi-family-journey-2026/index.html")
OUT = Path("_site")
ASSETS = OUT / "assets"

text = SRC.read_text(encoding="utf-8")

# Correct five source filenames that were 404 on Wikimedia Commons.
REPLACEMENTS = {
    "https://commons.wikimedia.org/wiki/Special:Redirect/file/Elephant%20Trunk%20Hill%20Guilin.jpg?width=1200":
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/ElephantTrunkHill.jpg?width=1200",
    "https://commons.wikimedia.org/wiki/Special:Redirect/file/Longji%20rice%20terraces%20Guangxi.jpg?width=1200":
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Longji%20rice%20terraces.jpg?width=1200",
    "https://commons.wikimedia.org/wiki/Special:Redirect/file/Li%20River%20China.jpg?width=1200":
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Li%20River%20cruise%20from%20Guilin%20to%20Yangshuo.JPG?width=1200",
    "https://commons.wikimedia.org/wiki/Special:Redirect/file/Detian%20Waterfall.jpg?width=1200":
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Full%20Sight%20for%20Detian%20Waterfalls%20%26%20Ban%20Gioc%20Waterfalls.jpg?width=1200",
    "https://commons.wikimedia.org/wiki/Special:Redirect/file/Ban%20Gioc%20-%20Detian%20Falls.jpg?width=1200":
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Ban%20Gioc%20-%20Detian%20Falls14.jpg?width=1200",
}
for old, new in REPLACEMENTS.items():
    text = text.replace(old, new)

OUT.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)

urls = list(dict.fromkeys(re.findall(
    r'src="(https://commons\.wikimedia\.org/wiki/Special:Redirect/file/[^"]+)"',
    text,
)))

fallback = ASSETS / "fallback.svg"
fallback.write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#dbe9df"/><stop offset="1" stop-color="#8fb3a6"/></linearGradient></defs>
<rect width="1200" height="800" fill="url(#g)"/><path d="M0 620L280 340l170 170 180-250 190 210 160-130 220 280v180H0z" fill="#315e53" opacity=".7"/><circle cx="930" cy="180" r="78" fill="#f3d39a"/><text x="600" y="720" text-anchor="middle" font-size="42" fill="#f8fbf9" font-family="sans-serif">广西 · 山水到海</text></svg>''', encoding="utf-8")


def fetch_one(item: tuple[int, str]):
    i, raw_url = item
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
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
            ctype = (r.headers.get_content_type() or "").lower()
            if not ctype.startswith("image/"):
                raise RuntimeError(f"unexpected content-type {ctype}")
            ext = mimetypes.guess_extension(ctype) or ".jpg"
            if ext == ".jpe":
                ext = ".jpg"
            name = f"travel-{i:02d}-{digest}{ext}"
            (ASSETS / name).write_bytes(data)
            return raw_url, f"assets/{name}", f"OK {i:02d}: {ctype} {len(data)} bytes -> {name}"
    except Exception as e:
        return raw_url, "assets/fallback.svg", f"FAILED {i:02d}: {url} :: {e}"


with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(fetch_one, list(enumerate(urls, start=1))))

ok = 0
failed = 0
for raw_url, local, message in results:
    text = text.replace(raw_url, local)
    if local == "assets/fallback.svg":
        failed += 1
        print(message, file=sys.stderr)
    else:
        ok += 1
        print(message)

(OUT / "index.html").write_text(text, encoding="utf-8")
print(f"Cached {ok}/{len(urls)} unique remote images locally; fallback={failed}.")
