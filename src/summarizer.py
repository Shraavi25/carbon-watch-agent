"""
summarizer.py — uses Groq (llama-3.3-70b-versatile) to produce a plain-English
summary of carbon market content, framed for Indian businesses.
"""

import logging
import os

from dotenv import load_dotenv
from groq import Groq, APIError, APIConnectionError, RateLimitError

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "llama-3.3-70b-versatile"

# Truncate content to this many characters before sending to the API —
# keeps token usage predictable and well within the model's context window.
CONTENT_CHAR_LIMIT = 3000

SYSTEM_PROMPT = (
    "You are a senior carbon market analyst specialising in regulatory policy. "
    "Your audience is Indian businesses that participate in or are affected by "
    "carbon markets — including compliance obligations under India's Carbon Credit "
    "Trading Scheme (CCTS), international voluntary carbon standards, and related "
    "environmental regulations. "
    "Summarise updates concisely, highlight practical implications, and flag any "
    "action items that Indian businesses should consider."
)


# ---------------------------------------------------------------------------
# Summariser
# ---------------------------------------------------------------------------

def summarise(site_name: str, url: str, content: str) -> str:
    """
    Call the Groq API to summarise `content` from `site_name` / `url`.

    Returns a plain-string summary (bullet points) or an error message if
    the API call fails.

    Args:
        site_name: Human-readable name of the source site.
        url:       URL the content was scraped from.
        content:   Raw extracted text; only the first CONTENT_CHAR_LIMIT chars are sent.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Fail early with a clear message rather than a cryptic auth error
        logger.error("GROQ_API_KEY is not set in the environment or .env file.")
        return "Error: GROQ_API_KEY is missing — cannot generate summary."

    # Truncate content so we stay within a predictable token budget
    truncated = content[:CONTENT_CHAR_LIMIT]

    user_prompt = (
        f"Source: {site_name}\n"
        f"URL: {url}\n\n"
        f"Content:\n{truncated}\n\n"
        "Please provide a summary covering:\n"
        "• What has changed or been announced\n"
        "• Why it matters for Indian businesses\n"
        "• Any action required or recommended\n\n"
        "Keep your response to a maximum of 5 bullet points. "
        "Be specific and practical — avoid generic statements."
    )

    client = Groq(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            # temperature=0 gives deterministic, factual summaries
            temperature=0,
        )
        summary = response.choices[0].message.content.strip()
        return summary

    except RateLimitError:
        logger.error("Groq rate limit hit for %s.", site_name)
        return "Error: Groq API rate limit reached — try again shortly."

    except APIConnectionError as exc:
        logger.error("Could not connect to Groq API for %s: %s", site_name, exc)
        return f"Error: Could not connect to Groq API — {exc}"

    except APIError as exc:
        # Covers 4xx/5xx responses not handled by the more specific subclasses above
        logger.error("Groq API error for %s: %s", site_name, exc)
        return f"Error: Groq API returned an error — {exc}"


# ---------------------------------------------------------------------------
# CLI entry point — quick manual test with a dummy payload
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    sample_content = (
        "India's Carbon Credit Trading Scheme (CCTS) has entered its mandatory phase. "
        "Obligated entities in energy-intensive sectors must now surrender carbon credits "
        "equivalent to their excess emissions. The Bureau of Energy Efficiency (BEE) has "
        "published updated baseline norms for steel, cement, and aluminium sectors. "
        "Non-compliance attracts a penalty of ₹5 lakh per excess tonne of CO2. "
        "Registration on the national carbon registry opens 1 July 2026."
    )

    result = summarise(
        site_name="BEE India Carbon Market",
        url="https://beeindia.gov.in/carbon-market.php",
        content=sample_content,
    )

    print("\n--- Summary ---")
    print(result)
