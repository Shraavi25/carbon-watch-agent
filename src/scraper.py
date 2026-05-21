"""
scraper.py — fetches carbon market pages, detects new content via hash comparison,
and persists seen-hashes to data/last_seen.json.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import TypedDict

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load any .env variables (e.g. custom DATA_DIR overrides) before anything else
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve paths relative to this file so the script works from any cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", _PROJECT_ROOT / "data"))
LAST_SEEN_FILE = DATA_DIR / "last_seen.json"

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

# Browser-like User-Agent to reduce the chance of being blocked
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Sites to monitor. Each entry is (human-readable name, URL).
SITES: list[tuple[str, str]] = [
    ("BEE India Carbon Market", "https://beeindia.gov.in/carbon-market.php"),
    ("ICAP News", "https://icapcarbonaction.com/en/news"),
    ("Verra News", "https://verra.org/news/"),
    ("MoEF India", "https://moef.gov.in"),
]


# ---------------------------------------------------------------------------
# TypedDict for the returned result objects
# ---------------------------------------------------------------------------

class SiteResult(TypedDict):
    site_name: str
    url: str
    new_content: str   # extracted text content from the page
    is_new: bool       # True when content hash differs from last run


# ---------------------------------------------------------------------------
# Hash / persistence helpers
# ---------------------------------------------------------------------------

def _load_last_seen() -> dict[str, str]:
    """Return the stored {url: hash} mapping, or an empty dict if missing."""
    try:
        with open(LAST_SEEN_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_last_seen(hashes: dict[str, str]) -> None:
    """Persist the updated {url: hash} mapping to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LAST_SEEN_FILE, "w", encoding="utf-8") as fh:
        json.dump(hashes, fh, indent=2)


def _content_hash(text: str) -> str:
    """Return an MD5 hex digest of the normalised text (fast, non-cryptographic use)."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Page fetching and text extraction
# ---------------------------------------------------------------------------

def _fetch_page(url: str) -> str | None:
    """
    Download a page and return its raw HTML, or None on any network error.
    Uses a browser User-Agent and the configured timeout.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        logger.error("Timeout fetching %s (limit: %ss)", url, REQUEST_TIMEOUT)
    except requests.exceptions.HTTPError as exc:
        logger.error("HTTP error fetching %s: %s", url, exc)
    except requests.exceptions.RequestException as exc:
        logger.error("Network error fetching %s: %s", url, exc)
    return None


def _extract_text(html: str) -> str:
    """
    Pull meaningful text from the page: all headings (h1-h4) and paragraphs.
    Returns a single whitespace-normalised string suitable for hashing and display.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove navigation, footer, and script noise so hash changes reflect real content
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    chunks: list[str] = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "p"]):
        text = element.get_text(separator=" ", strip=True)
        if text:
            chunks.append(text)

    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# Main scraping entry point
# ---------------------------------------------------------------------------

def scrape_all() -> list[SiteResult]:
    """
    Scrape all configured sites and return a list of SiteResult dicts.

    For each site:
      1. Fetch the page (skip on error, log and continue).
      2. Extract heading/paragraph text.
      3. Compare its hash to the stored hash in last_seen.json.
      4. Mark is_new=True if the hash changed (or the site was never seen before).
      5. Update the in-memory hash map; persist it to disk once at the end.
    """
    last_seen = _load_last_seen()
    results: list[SiteResult] = []

    for site_name, url in SITES:
        logger.info("Checking %s (%s)", site_name, url)

        html = _fetch_page(url)
        if html is None:
            # Site unreachable — skip without updating the stored hash so we retry next run
            logger.warning("Skipping %s due to fetch error.", site_name)
            continue

        content = _extract_text(html)
        current_hash = _content_hash(content)
        previous_hash = last_seen.get(url)

        is_new = current_hash != previous_hash
        if is_new:
            logger.info("  -> New content detected on %s", site_name)
        else:
            logger.info("  -> No change on %s", site_name)

        # Update the hash so the next run uses the current state as baseline
        last_seen[url] = current_hash

        results.append(
            SiteResult(
                site_name=site_name,
                url=url,
                new_content=content,
                is_new=is_new,
            )
        )

    # Persist all updated hashes in a single write at the end of the run
    _save_last_seen(last_seen)

    return results


# ---------------------------------------------------------------------------
# CLI entry point — useful for quick manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    updates = scrape_all()
    print(f"\n{'='*60}")
    print(f"Scraped {len(updates)} site(s)")
    for r in updates:
        status = "NEW" if r["is_new"] else "unchanged"
        print(f"\n[{status}] {r['site_name']}\n  {r['url']}")
        if r["is_new"]:
            # Print a preview of the first 400 characters of new content
            preview = r["new_content"][:400].replace("\n", " ")
            print(f"  Preview: {preview}...")
