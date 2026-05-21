"""
emailer.py — sends a formatted HTML digest email via the Resend SDK.

Main entry point: send_digest(updates)
  updates: list of dicts with keys site_name (str), url (str), summary (str)
"""

import logging
import os
from datetime import date
from typing import TypedDict

import resend
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Sender address must be a verified domain in your Resend account.
# Using onboarding@resend.dev works for testing on free tier.
FROM_ADDRESS = os.getenv("FROM_EMAIL", "onboarding@resend.dev")


# ---------------------------------------------------------------------------
# TypedDict for one update entry passed into send_digest
# ---------------------------------------------------------------------------

class UpdateEntry(TypedDict):
    site_name: str
    url: str
    summary: str   # plain-text bullet points returned by summarizer.py


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def _summary_to_html(summary: str) -> str:
    """
    Convert the LLM's plain-text bullet output into an HTML <ul> list.

    Lines starting with '•', '-', or '*' become <li> items.
    Any other non-empty lines are wrapped in a <p> (e.g. a preamble sentence).
    """
    lines = summary.strip().splitlines()
    parts: list[str] = []
    list_items: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith(("•", "-", "*")):
            # Strip the bullet character and any leading whitespace
            list_items.append(f"<li>{stripped.lstrip('•-* ').strip()}</li>")
        else:
            # Flush any accumulated list items before the prose line
            if list_items:
                parts.append("<ul>" + "".join(list_items) + "</ul>")
                list_items = []
            parts.append(f"<p>{stripped}</p>")

    # Flush any remaining list items
    if list_items:
        parts.append("<ul>" + "".join(list_items) + "</ul>")

    return "".join(parts)


def _build_html(updates: list[UpdateEntry]) -> str:
    """
    Render the full HTML email body from a list of update entries.
    Inline styles are used for broad email client compatibility.
    """
    today = date.today().strftime("%B %d, %Y")

    # --- Header section ---
    header = f"""
    <div style="background:#1a472a;padding:24px 32px;border-radius:6px 6px 0 0;">
      <h1 style="margin:0;color:#ffffff;font-family:Arial,sans-serif;font-size:22px;">
        Carbon Market Update
      </h1>
      <p style="margin:4px 0 0;color:#a8d5b5;font-family:Arial,sans-serif;font-size:14px;">
        {today}
      </p>
    </div>
    """

    # --- One section per update ---
    sections: list[str] = []
    for entry in updates:
        summary_html = _summary_to_html(entry["summary"])
        section = f"""
        <div style="border-left:4px solid #2d7a4f;padding:16px 20px;margin:20px 0;
                    background:#f9fdf9;border-radius:0 4px 4px 0;">
          <h2 style="margin:0 0 4px;font-family:Arial,sans-serif;font-size:17px;color:#1a472a;">
            {entry['site_name']}
          </h2>
          <p style="margin:0 0 12px;">
            <a href="{entry['url']}"
               style="font-family:Arial,sans-serif;font-size:12px;color:#5a9e75;
                      text-decoration:none;">
              {entry['url']}
            </a>
          </p>
          <div style="font-family:Arial,sans-serif;font-size:14px;color:#333;line-height:1.6;">
            {summary_html}
          </div>
        </div>
        """
        sections.append(section)

    # If there are no updates, show a friendly notice instead of a blank email
    body_content = "".join(sections) if sections else (
        "<p style='font-family:Arial,sans-serif;color:#666;font-size:14px;'>"
        "No new carbon market updates detected in this run.</p>"
    )

    footer = """
    <p style="font-family:Arial,sans-serif;font-size:11px;color:#999;
              border-top:1px solid #e0e0e0;padding-top:12px;margin-top:24px;">
      Sent by Carbon Watch Agent &mdash; automated regulatory monitoring for Indian businesses.
    </p>
    """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:24px;background:#f0f4f0;">
      <div style="max-width:680px;margin:0 auto;background:#ffffff;
                  border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        {header}
        <div style="padding:8px 32px 24px;">
          {body_content}
          {footer}
        </div>
      </div>
    </body>
    </html>
    """


# ---------------------------------------------------------------------------
# Main send function
# ---------------------------------------------------------------------------

def send_digest(updates: list[UpdateEntry]) -> bool:
    """
    Send the HTML digest email to ALERT_EMAIL via Resend.

    Args:
        updates: list of dicts with site_name, url, and summary keys.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    api_key = os.getenv("RESEND_API_KEY")
    to_address = os.getenv("ALERT_EMAIL")

    # Validate required config before making any API calls
    if not api_key:
        logger.error("RESEND_API_KEY is not set — cannot send email.")
        return False
    if not to_address:
        logger.error("ALERT_EMAIL is not set — no recipient configured.")
        return False

    resend.api_key = api_key

    today_label = date.today().strftime("%Y-%m-%d")
    subject = f"Carbon Market Update — {today_label}"

    html_body = _build_html(updates)

    try:
        response = resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [to_address],
            "subject": subject,
            "html": html_body,
        })
        # Resend returns an object with an `id` field on success
        email_id = getattr(response, "id", response)
        logger.info("Digest email sent successfully (id: %s) to %s", email_id, to_address)
        return True

    except Exception as exc:
        # Catch-all so a broken email send never crashes the main pipeline
        logger.error("Failed to send digest email: %s", exc)
        return False


# ---------------------------------------------------------------------------
# CLI test block — sends a real email with dummy data
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    dummy_updates: list[UpdateEntry] = [
        {
            "site_name": "BEE India Carbon Market",
            "url": "https://beeindia.gov.in/carbon-market.php",
            "summary": (
                "Here are the key updates:\n"
                "• India's CCTS has entered its mandatory compliance phase for energy-intensive sectors.\n"
                "• BEE has published updated baseline norms for steel, cement, and aluminium.\n"
                "• Non-compliance penalty is ₹5 lakh per excess tonne of CO2.\n"
                "• National carbon registry registration opens 1 July 2026.\n"
                "• Businesses should audit their emissions against new baselines immediately."
            ),
        },
        {
            "site_name": "ICAP News",
            "url": "https://icapcarbonaction.com/en/news",
            "summary": (
                "Key highlights from ICAP:\n"
                "• EU, Brazil, and China have formally launched an Open Coalition on Compliance Carbon Markets.\n"
                "• India's CCTS compliance obligations are now internationally recognised under this coalition.\n"
                "• The ICAP Status Report 2026 notes steady growth despite geopolitical turbulence.\n"
                "• Indian exporters to the EU should monitor the EU Carbon Border Adjustment Mechanism timeline.\n"
                "• No immediate action required, but coalition membership may affect future credit recognition."
            ),
        },
    ]

    success = send_digest(dummy_updates)
    print("Email sent:", success)
