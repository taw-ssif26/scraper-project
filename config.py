import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")           # "groq" | "openrouter"
LLM_MODEL    = os.getenv("LLM_MODEL", "llama3-8b-8192")
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "")

# ── Browser ───────────────────────────────────────────────────────────────────
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
SCRAPING_API     = os.getenv("SCRAPING_API", "")        # "scrapingbee" or "zenrows"
SCRAPING_API_KEY = os.getenv("SCRAPING_API_KEY", "")
# ── Proxy (disabled at MVP) ───────────────────────────────────────────────────
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"
PROXY_URL     = os.getenv("PROXY_URL", "")

# ── Scraper behaviour ─────────────────────────────────────────────────────────
PAGE_TIMEOUT_MS     = 30_000   # how long to wait for a page to load
NAVIGATION_DELAY_MS = 1_500    # pause between actions (human-like)
MAX_RETRIES         = 3        # retries on navigation failure
MAX_PAGES           = 50       # safety cap — stop after this many pages

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "output_files"    # folder where CSV/JSON are saved
