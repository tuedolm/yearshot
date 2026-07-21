#!/usr/bin/env python3
"""Localize library images for CDN hosting.

Downloads each library image from Wikimedia Commons (at IMAGE_WIDTH) into
assets/, named by image id. Run this before launch, upload assets/ to your
CDN/host, then point tools/generate_puzzles.py's image_url() at the CDN base
and regenerate the puzzle blobs. Hotlinking Commons is fine for a prototype
but rude and fragile at public traffic levels.

Usage:
    python3 tools/fetch_images.py          # download anything missing
    python3 tools/fetch_images.py --force  # re-download everything

Be a good citizen: this sends a descriptive User-Agent and paces requests.
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "content" / "library.json"
ASSETS = ROOT / "assets"
IMAGE_WIDTH = 1600
USER_AGENT = "TimelineDailyGame/1.0 (image localization for a daily puzzle; run by the repo owner)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    lib = json.loads(LIBRARY.read_text())
    ASSETS.mkdir(exist_ok=True)
    done = skipped = failed = 0

    for img in lib["images"]:
        dest = ASSETS / f"{img['id']}.jpg"
        if dest.exists() and not args.force:
            skipped += 1
            continue
        url = (
            "https://commons.wikimedia.org/wiki/Special:FilePath/"
            + urllib.parse.quote(img["commonsFile"])
            + f"?width={IMAGE_WIDTH}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        ok = False
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    dest.write_bytes(resp.read())
                ok = True
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:  # robot-policy rate limit: back off hard
                    time.sleep(15 * (attempt + 1))
                    continue
                print(f"  FAILED {img['id']}: {e}")
                break
            except Exception as e:  # noqa: BLE001 - report and continue
                print(f"  FAILED {img['id']}: {e}")
                break
        if ok:
            print(f"  fetched {dest.name}")
            done += 1
        else:
            failed += 1
        time.sleep(4)  # pace requests per Wikimedia robot policy

    print(f"done: {done} fetched, {skipped} already present, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
