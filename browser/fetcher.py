# browser/fetcher.py

import httpx
import config

async def fetch_page_html(page, url: str) -> str:
    """
    Try Playwright first.
    If page looks blocked, fall back to scraping API.
    Returns raw HTML either way.
    """
    import asyncio

    # Wait a moment for any remaining JS to finish
    await asyncio.sleep(2)

    # Try page.content() first
    html = await page.content()

    # If empty, try evaluate as fallback
    if not html or len(html.strip()) < 100:
        try:
            html = await page.evaluate("document.documentElement.outerHTML")
        except Exception:
            pass

    # If still empty, wait more and retry
    if not html or len(html.strip()) < 100:
        await asyncio.sleep(3)
        try:
            html = await page.evaluate("document.documentElement.outerHTML")
        except Exception:
            pass

    # Check if we got real content or a block page
    if _is_blocked(html):
        print(f"[Fetcher] Blocked by site. Trying API fallback...")
        return await _fetch_via_api(url)

    return html


def _is_blocked(html: str) -> bool:
    """Detect common block page signatures."""
    html_lower = html.lower()
    signals = [
        "checking your browser",
        "enable javascript and cookies",
        "ddos protection",
        "ray id",                    # Cloudflare
        "cf-browser-verification",
        "access denied",
        "403 forbidden",
        "blocked",
        "unusual traffic",
        len(html) < 1500,            # suspiciously short page
    ]
    return any(signals[:-1]) or signals[-1]


async def _fetch_via_api(url: str) -> str:
    """Fetch via ScrapingBee or ZenRows API."""
    if config.SCRAPING_API == "scrapingbee":
        return await _scrapingbee(url)
    elif config.SCRAPING_API == "zenrows":
        return await _zenrows(url)
    return ""


async def _scrapingbee(url: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            "https://app.scrapingbee.com/api/v1/",
            params={
                "api_key": config.SCRAPING_API_KEY,
                "url": url,
                "render_js": "true",
                "premium_proxy": "true",
            }
        )
        if response.status_code == 200:
            return response.text
        print(f"[Fetcher] ScrapingBee error: {response.status_code}")
        return ""


async def _zenrows(url: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            "https://api.zenrows.com/v1/",
            params={
                "apikey": config.SCRAPING_API_KEY,
                "url": url,
                "js_render": "true",
                "premium_proxy": "true",
            }
        )
        if response.status_code == 200:
            return response.text
        print(f"[Fetcher] ZenRows error: {response.status_code}")
        return ""
