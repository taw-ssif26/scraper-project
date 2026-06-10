import asyncio
from enum import Enum
from browser.engine import BrowserEngine
from browser.captcha_detector import is_captcha_page
from browser.dom_cleaner import clean_html
from output.writer import save_results
import config
from browser.fetcher import fetch_page_html

class State(Enum):
    IDLE     = "idle"
    RUNNING  = "running"
    PAUSED   = "paused"
    COMPLETE = "complete"
    STOPPED  = "stopped"
    ERROR    = "error"


# Signals that indicate a hard block — not a captcha, just rejected
_BLOCK_SIGNALS = [
    "access denied",
    "403 forbidden",
    "ddos protection by",
    "unusual traffic from your computer",
    "your ip has been blocked",
    "this page is not available in your region",
    "you have been blocked",
    "enable javascript and cookies to continue",
    "ray id",
]


class Orchestrator:
    def __init__(self, log_callback=None):
        self.state = State.IDLE
        self.browser = BrowserEngine()
        self.records = []
        self.output_paths = {}
        self._log = log_callback or print
        self._captcha_resolved = asyncio.Event()

    async def run(self, url: str, task: str):
        self._transition(State.RUNNING)
        self.records = []
        try:
            self._log("Launching browser...")
            await self.browser.launch()
            await self._scrape_loop(url, task)
        except Exception as e:
            self._log(f"Fatal error: {e}")
            self._transition(State.ERROR)
        finally:
            await self.browser.close()
        if self.state not in (State.STOPPED, State.ERROR):
            self._transition(State.COMPLETE)
            self._log(f"Done. {len(self.records)} records collected.")

    def stop(self):
        self._log("Stopping...")
        self._transition(State.STOPPED)
        self._captcha_resolved.set()

    def resolve_captcha(self):
        self._log("Captcha resolved. Resuming...")
        self._transition(State.RUNNING)
        self._captcha_resolved.set()

    async def _scrape_loop(self, start_url: str, task: str):
        from urllib.parse import urlparse
        from extractor.structure_cache import get_structure, save_structure
        from extractor.fast_extractor import extract_with_structure, structure_seems_broken
        from extractor.llm_client import learn_structure

        domain = urlparse(start_url).netloc
        url = start_url
        pages_scraped = 0

        while self.state == State.RUNNING and pages_scraped < config.MAX_PAGES:
            self._log(f"Navigating to: {url}")
            success = await self.browser.navigate(url)

            if not success:
                self._log(f"Failed to load: {url}")
                break

            # Get raw HTML for analysis
            raw_html = await fetch_page_html(self.browser.page, url)
            self._log(f"[Diag] URL after nav: {self.browser.page.url}")
            self._log(f"[Diag] HTML length: {len(raw_html)}")
            self._log(f"[Diag] HTML start: {raw_html[:200]}")

            # Check for captcha first — pause and let user solve
            if await is_captcha_page(self.browser.page):
                await self._handle_captcha()
                if self.state != State.RUNNING:
                    break
                # Re-fetch HTML after captcha solved
                rraw_html = await fetch_page_html(self.browser.page, url)

            # Check for hard block — not solvable, inform user and stop
            block_reason = self._detect_block(raw_html)
            if block_reason:
                self._log(f"🚫 Blocked by site: {block_reason}")
                self._log("This site rejected the request. Possible fixes:")
                self._log("  1. Enable a residential proxy in .env (PROXY_ENABLED=true)")
                self._log("  2. Try again later — some blocks are temporary")
                self._log("  3. This site may require a scraping API service")
                break

            await self.browser.scroll_to_bottom()

            structure = get_structure(domain)
            cache_hit = structure is not None

            if structure:
                self._log(f"Page {pages_scraped + 1}: using cached structure...")
                page_records = await extract_with_structure(self.browser.page, structure)
                if structure_seems_broken(page_records):
                    self._log("Structure outdated. Re-learning...")
                    structure = None
                    cache_hit = False

            if not structure:
                self._log(f"Page {pages_scraped + 1}: learning structure via LLM...")
                main_html = await self.browser.get_main_content_html()
                await asyncio.sleep(2)
                structure = await learn_structure(main_html, task)
                if structure:
                    if not cache_hit:
                        save_structure(domain, structure)
                        self._log("Structure learned and cached.")
                    page_records = await extract_with_structure(self.browser.page, structure)
                else:
                    self._log("Structure learning failed. Skipping page.")
                    page_records = []

            if page_records:
                self.records.extend(page_records)
                self._log(f"  -> {len(page_records)} records (total: {len(self.records)})")
            else:
                self._log("  -> No records found on this page.")

            pages_scraped += 1
            next_url = await self._find_next_page()
            if next_url:
                url = next_url
            else:
                self._log("No more pages.")
                break

        if self.records:
            self.output_paths = save_results(self.records)
            self._log(f"Saved: {self.output_paths}")
        else:
            if self.state == State.RUNNING:
                self._log("No data collected.")

    def _detect_block(self, html: str) -> str | None:
        """
        Check HTML for hard block signals.
        Returns a description string if blocked, None if clean.
        Does NOT flag captcha pages — those are handled separately.
        """
        html_lower = html.lower()

        # Suspiciously short page — likely a block or redirect
        if len(html.strip()) < 1200:
            return "Page too short — likely a block or empty response"

        for signal in _BLOCK_SIGNALS:
            if signal in html_lower:
                return f'"{signal}" detected in page'

        return None

    async def _handle_captcha(self):
        self._transition(State.PAUSED)
        self._captcha_resolved.clear()
        self._log("⚠️ CAPTCHA DETECTED — Please solve it in the browser window, then click Resume.")
        await self._captcha_resolved.wait()

    async def _find_next_page(self):
        selectors = [
            "a[rel='next']",
            "a.next",
            "a.pagination-next",
            "li.next a",
            "a:has-text('Next')",
            "a:has-text('next')",
            "a:has-text('›')",
            "a:has-text('»')",
        ]
        for selector in selectors:
            try:
                element = await self.browser.page.query_selector(selector)
                if element:
                    href = await element.get_attribute("href")
                    if href and href not in ("#", "javascript:void(0)"):
                        return await self.browser.page.evaluate(
                            "(href) => new URL(href, window.location.href).href",
                            href
                        )
            except Exception:
                continue
        return None

    def _transition(self, new_state: State):
        self.state = new_state
        self._log(f"[State] -> {new_state.value}")
