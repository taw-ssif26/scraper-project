from playwright.async_api import Page

# Keywords in page title that indicate a challenge page
_TITLE_KEYWORDS = [
    "captcha", "verify", "verification", "robot", "security check",
    "human", "challenge", "blocked", "access denied", "attention required"
]

# DOM selectors that appear on known captcha/challenge pages
_CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "iframe[src*='turnstile']",
    "#cf-challenge-running",        # Cloudflare
    ".cf-browser-verification",     # Cloudflare
    "#challenge-form",              # Cloudflare
    "[data-sitekey]",               # Generic captcha widget
    "#px-captcha",                  # PerimeterX
    ".g-recaptcha",                 # Google reCAPTCHA
    ".h-captcha",                   # hCaptcha
]

# URL fragments that signal a challenge redirect
_CHALLENGE_URL_FRAGMENTS = [
    "captcha", "challenge", "verify", "bot-check", "security"
]


async def is_captcha_page(page: Page) -> bool:
    """
    Returns True if the current page looks like a bot challenge.
    Checks title, DOM elements, and URL.
    """
    # Check 1: page title
    try:
        title = (await page.title()).lower()
        if any(kw in title for kw in _TITLE_KEYWORDS):
            return True
    except Exception:
        pass

    # Check 2: known captcha DOM elements
    for selector in _CAPTCHA_SELECTORS:
        try:
            element = await page.query_selector(selector)
            if element:
                return True
        except Exception:
            continue

    # Check 3: challenge URL
    try:
        url = page.url.lower()
        if any(fragment in url for fragment in _CHALLENGE_URL_FRAGMENTS):
            return True
    except Exception:
        pass

    return False
