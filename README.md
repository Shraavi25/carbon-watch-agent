# 🌱 Carbon Watch Agent

An autonomous AI agent that monitors Indian carbon market regulatory websites daily and delivers a summarised email digest — powered by LLaMA 3.3, Groq, and GitHub Actions.

**Built as Project 1 of a carbon credits AI consultancy startup.**

---

## What It Does

India's carbon market is evolving fast — BEE's compliance trading system, Verra's voluntary credits, ICAP policy updates, and MoEF environment notifications. Businesses miss critical regulatory changes because the information is scattered across multiple websites.

This agent solves that by:

1. **Scraping** 4 regulatory websites every morning
2. **Detecting changes** using MD5 content hashing (only acts when something actually changed)
3. **Summarising** new content via LLaMA 3.3 70B on Groq — written for an Indian business audience
4. **Emailing** a clean HTML digest — silent if nothing changed

Total infrastructure cost: **₹0/month**

---

## Architecture

```
GitHub Actions (cron: 8am IST daily)
        │
        ▼
   scraper.py        ← fetches 4 sites, detects changes via MD5 hash
        │
        ▼ (only if changes found)
  summarizer.py      ← calls Groq API (LLaMA 3.3 70B) with carbon analyst prompt
        │
        ▼
   emailer.py        ← sends HTML digest via Resend
```

**Orchestrated by** `agent.py` → **triggered by** `main.py`

---

## Sites Monitored

| Site | URL |
|------|-----|
| BEE India Carbon Market | https://beeindia.gov.in/carbon-market.php |
| ICAP Carbon Action | https://icapcarbonaction.com/en/news |
| Verra News | https://verra.org/news/ |
| MoEF India | https://moef.gov.in |

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Web scraping | `requests` + `BeautifulSoup` | Lightweight HTML fetching and parsing |
| Change detection | MD5 hashing + `last_seen.json` | Persistent memory between runs, zero database needed |
| LLM inference | Groq API — `llama-3.3-70b-versatile` | Free tier, fast, high quality open-source model |
| Email delivery | Resend API | Simple transactional email, generous free tier |
| Scheduling | GitHub Actions (cron) | Free cloud compute, no always-on server needed |
| Secret management | GitHub Secrets | API keys never in code or version history |

---

## Project Structure

```
carbon-watch-agent/
├── src/
│   ├── agent.py          # Orchestrator: scrape → summarise → email
│   ├── scraper.py        # Fetches sites, detects content changes
│   ├── summarizer.py     # Groq LLM summarisation
│   └── emailer.py        # HTML email digest via Resend
├── data/
│   └── last_seen.json    # Auto-generated: MD5 hashes of last seen content
├── .github/
│   └── workflows/
│       └── carbon-watch.yml   # GitHub Actions: daily cron at 8am IST
├── main.py               # Entry point
├── requirements.txt
└── .env                  # Local only — never committed
```

---

## Setup & Run Locally

**1. Clone the repo**
```bash
git clone https://github.com/Shraavi25/carbon-watch-agent.git
cd carbon-watch-agent
```

**2. Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
```

**3. Install dependencies**
```bash
pip install groq requests beautifulsoup4 python-dotenv resend lxml
```

**4. Add your API keys**

Create a `.env` file (never commit this):
```
GROQ_API_KEY=your_groq_key_here
RESEND_API_KEY=your_resend_key_here
ALERT_EMAIL=your@email.com
```

**5. Run the agent**
```bash
python main.py
```

---

## Cloud Deployment (GitHub Actions)

The agent runs automatically every day at 8am IST via `.github/workflows/carbon-watch.yml`.

To set up:
1. Add three **Repository Secrets** in GitHub → Settings → Secrets and variables → Actions:
   - `GROQ_API_KEY`
   - `RESEND_API_KEY`
   - `ALERT_EMAIL`
2. Go to Actions tab → Carbon Watch Agent → Run workflow (to test manually)

---

## API Keys & Resources

| Service | Free Tier | Sign Up |
|---------|-----------|---------|
| Groq (LLM inference) | 14,400 requests/day | [console.groq.com](https://console.groq.com) |
| Resend (email) | 100 emails/day, 3,000/month | [resend.com](https://resend.com) |
| GitHub Actions | 2,000 minutes/month | [github.com](https://github.com) |

---

## Learning Resources

### Carbon Markets
- [GHG Protocol — Corporate Standard](https://ghgprotocol.org/corporate-standard) — the foundational framework for carbon accounting
- [Verra VCS Standard](https://verra.org/programs/verified-carbon-standard/) — the world's leading voluntary carbon credit standard
- [ICAP — India ETS Overview](https://icapcarbonaction.com/en/ets/india) — India's emissions trading system tracker
- [BEE India Carbon Market](https://beeindia.gov.in/carbon-market.php) — Bureau of Energy Efficiency, India's carbon market regulator
- [India's Carbon Credit Trading Scheme (CCTS)](https://beeindia.gov.in/sites/default/files/CCTS%20Rules.pdf) — official government rules

### AI Agents & LLMs
- [Groq Documentation](https://console.groq.com/docs/openai) — fast LLM inference API
- [LLaMA 3.3 Model Card](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) — the model powering this agent
- [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) — how to write effective system prompts
- [BeautifulSoup Docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) — HTML parsing library used in scraper

### Tools Used
- [Resend Docs](https://resend.com/docs) — email delivery API
- [GitHub Actions — Cron Syntax](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule) — how the daily scheduling works
- [GitHub Secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions) — secure API key management

---

## About

Built by [@Shraavi25](https://github.com/Shraavi25) as part of a carbon credits AI consultancy startup focused on helping Indian businesses navigate the voluntary and compliance carbon markets.

This is Project 1 of a series of AI agents being built in this space.

---

*Part of a larger initiative to bring AI-native tools to India's emerging carbon market.*
