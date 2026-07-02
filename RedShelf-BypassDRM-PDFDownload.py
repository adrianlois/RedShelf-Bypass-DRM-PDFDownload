import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force utf-8 output
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import img2pdf
import requests

CONFIG_FILE  = "config.json"
COOKIES_FILE = "cookies.json"

_cfg = json.load(open(CONFIG_FILE))
target_directory_img = _cfg["target_directory_img"]
base_url             = _cfg["base_url"]
numpag               = _cfg["numpag"]
pdf_file             = os.path.join(target_directory_img, _cfg["pdf_filename"])
MAX_WORKERS          = _cfg.get("max_workers", 8)
MAX_RETRY_ROUNDS     = _cfg.get("max_retry_rounds", 5)
CF_WAIT_BUFFER       = _cfg.get("cf_wait_buffer", 15)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://platform.virdocs.com/",
}


# Helpers

def load_cookies(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return {c["name"]: c["value"] for c in data}
    return data


def cf_ttl_remaining(response):
    """Returns seconds remaining until the Cloudflare cached 401 expires.
    Returns 0 if the response is not a CF cache HIT."""
    if response.headers.get("cf-cache-status") != "HIT":
        return 0
    max_age = 1800
    for part in response.headers.get("cache-control", "").split(","):
        part = part.strip()
        if part.startswith("max-age="):
            try:
                max_age = int(part[8:])
            except ValueError:
                pass
    age = int(response.headers.get("age", 0))
    return max(0, max_age - age) + CF_WAIT_BUFFER


def countdown(seconds):
    for remaining in range(seconds, 0, -1):
        m, s = divmod(remaining, 60)
        print(f"\r  ⏳  Retrying in {m:02d}:{s:02d} ...", end="", flush=True)
        time.sleep(1)
    print(f"\r  ✔  Wait complete. Resuming...                          ")


def sep(char="─", width=60):
    print(char * width)


# Single page download

def download_page(pg, cookies):
    """Returns (pg, status, extra).
    status: 'skip' | 'ok' | 'cf_blocked' | 'auth_error' | 'error'
    extra:  remaining TTL if cf_blocked, 0 otherwise
    """
    file_name = os.path.join(target_directory_img, f"{pg}.jpg")
    if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
        return pg, "skip", 0

    url = base_url.format(pg)
    for attempt in range(1, 4):
        try:
            r = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                with open(file_name, "wb") as f:
                    f.write(r.content)
                return pg, "ok", 0
            if r.status_code == 401:
                ttl = cf_ttl_remaining(r)
                return pg, "cf_blocked" if ttl > 0 else "auth_error", ttl
            # other HTTP code - retry
        except requests.RequestException:
            pass
        if attempt < 3:
            time.sleep(2)

    return pg, "error", 0


# Download round

def run_round(pages, cookies, round_num):
    """Downloads pages in parallel and returns grouped results."""
    ok, cf_blocked, auth_errors, errors = [], {}, [], []

    total   = len(pages)
    counter = [0]
    lock    = threading.Lock()

    def on_done(pg, status, extra):
        with lock:
            counter[0] += 1
            done = counter[0]
            pct  = done * 100 // total
            bar  = "█" * (pct // 5) + "░" * (20 - pct // 5)
            tag  = {"ok": "OK", "skip": "SKIP", "cf_blocked": "CF-BLOQ",
                    "auth_error": "AUTH!", "error": "ERR"}[status]
            print(
                f"\r  [{bar}] {pct:3d}%  {done:>4}/{total}  [{tag}] p.{pg:<5}",
                end="", flush=True
            )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(download_page, pg, cookies): pg for pg in pages}
        for future in as_completed(futures):
            pg, status, extra = future.result()
            on_done(pg, status, extra)
            if status in ("ok", "skip"):
                ok.append(pg)
            elif status == "cf_blocked":
                cf_blocked[pg] = extra
            elif status == "auth_error":
                auth_errors.append(pg)
            else:
                errors.append(pg)

    print()  # newline after progress bar
    return ok, cf_blocked, auth_errors, errors


# Build PDF

def build_pdf(pages):
    print(f"\n  Building PDF with {len(pages)} pages...")
    paths = [os.path.join(target_directory_img, f"{pg}.jpg") for pg in sorted(pages)]
    # img2pdf embeds JPEGs directly without re-encoding -maximum quality
    a4 = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
    layout = img2pdf.get_layout_fun(a4)
    with open(pdf_file, "wb") as f:
        f.write(img2pdf.convert(paths, layout_fun=layout))
    print(f"  PDF saved to: {pdf_file}")


# main

def main():
    sep("═")
    print("  RedShelf Virdocs - PDF Downloader")
    sep("═")

    os.makedirs(target_directory_img, exist_ok=True)

    try:
        cookies = load_cookies(COOKIES_FILE)
    except FileNotFoundError:
        print(f"\n  [ERROR] {COOKIES_FILE} not found. Place it next to the script.")
        sys.exit(1)

    print(f"  Cookies loaded    : [{' ; '.join(f'{k}={v}' for k, v in cookies.items())}]")
    print(f"  Total pages       : {numpag}")
    print(f"  Images directory  : {target_directory_img}")
    print(f"  PDF output        : {pdf_file}")
    sep()

    all_ok  = set()
    pending = list(range(1, numpag + 1))

    for round_num in range(1, MAX_RETRY_ROUNDS + 1):
        if not pending:
            break

        print(f"\n  Round {round_num} - {len(pending)} pages pending")
        sep("─")

        ok, cf_blocked, auth_errors, errors = run_round(pending, cookies, round_num)
        all_ok.update(ok)

        # round summary
        print(f"  ✔  OK/skip    : {len(ok)}")
        if cf_blocked:
            print(f"  ⏳  CF-blocked : {len(cf_blocked)}")
        if auth_errors:
            print(f"  ✖  Auth error : {len(auth_errors)}")
            print("    Check that cookies are valid and the book is open in the reader.")
        if errors:
            print(f"  ⚠  Network error  : {len(errors)}")

        # compute next round
        next_pending = list(cf_blocked.keys()) + errors

        if cf_blocked:
            wait = max(cf_blocked.values())
            sep()
            print(f"\n  Cloudflare cached {len(cf_blocked)} 401 responses.")
            print(f"  Max TTL detected: {wait}s")
            countdown(wait)

        if not next_pending:
            break

        pending = next_pending

        if not cf_blocked and errors:
            # network errors only: brief pause before retrying
            time.sleep(5)

    # Final summary
    sep("═")
    missing = [p for p in range(1, numpag + 1) if p not in all_ok]
    print(f"  Downloaded   : {len(all_ok)}/{numpag}")
    if missing:
        print(f"  Failed       : {len(missing)} -{missing[:20]}{'...' if len(missing) > 20 else ''}")
    sep("═")

    if not all_ok:
        print("\n  [ERROR] No pages downloaded. Check your cookies.")
        sys.exit(1)

    build_pdf(all_ok)
    sep("═")
    print("  Done!")
    sep("═")


if __name__ == "__main__":
    main()
