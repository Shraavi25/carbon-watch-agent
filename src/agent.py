"""
agent.py — orchestrates the full carbon-watch pipeline:
  scraper  →  summariser  →  emailer

Entry point: run_agent()
"""

import logging
import sys

from dotenv import load_dotenv

from .scraper import scrape_all
from .summarizer import summarise
from .emailer import send_digest, UpdateEntry

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_agent() -> None:
    """
    Run the full pipeline end-to-end:
      1. Scrape all configured sites and detect which have new content.
      2. For each new result, call the LLM summariser.
      3. If any summaries were produced, send a digest email.
    """

    # --- Step 1: scrape ---
    logger.info("Starting scrape of all sites...")
    results = scrape_all()
    logger.info("Scraped %d site(s).", len(results))

    # --- Step 2: filter and summarise ---
    # Only process sites where content changed since the last run
    new_results = [r for r in results if r["is_new"]]
    logger.info("%d site(s) have new content.", len(new_results))

    digest: list[UpdateEntry] = []

    for result in new_results:
        site_name = result["site_name"]
        url = result["url"]
        content = result["new_content"]

        logger.info("Summarising: %s", site_name)
        summary = summarise(site_name=site_name, url=url, content=content)

        # summarise() returns an error string on failure — include it in the
        # digest anyway so the recipient knows a site was seen but not parsed
        digest.append(
            UpdateEntry(
                site_name=site_name,
                url=url,
                summary=summary,
            )
        )

    # --- Step 3: email ---
    if not digest:
        logger.info("No updates found — skipping email.")
        return

    logger.info("Sending digest email with %d update(s)...", len(digest))
    sent = send_digest(digest)

    if sent:
        logger.info("Pipeline complete. %d update(s) emailed.", len(digest))
    else:
        logger.error("Pipeline complete but email delivery failed.")

    logger.info("Sites with new content this run: %d / %d", len(new_results), len(results))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Run as a module: python -m src.agent
    run_agent()
