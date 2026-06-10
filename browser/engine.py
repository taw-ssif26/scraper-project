import asyncio
import random
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import config


class BrowserEngine:
    def __init__(self):
        self._playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None
        self.page: Page = None

    async def launch(self):
        self._playwright = await async_playwright().start()

        launch_args = {
            "headless": False,
            "args": [
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-zygote",
            ]
        }

        if config.BROWSER_HEADLESS:
            launch_args["args"].append("--headless")

        if config.PROXY_ENABLED and config.PROXY_URL:
            launch_args["proxy"] = {"server": config.PROXY_URL}

        self._browser = await self._playwright.chromium.launch(**launch_args)

        width  = random.randint(1240, 1320)
        height = random.randint(768, 820)

        self._context = await self._browser.new_context(
            viewport={"width": width, "height": height},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
        )

        self.page = await self._context.new_page()

        # Comprehensive stealth — hides automation signals
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            delete navigator.__proto__.webdriver;

            window.chrome = {
                runtime: {
                    connect: () => {},
                    sendMessage: () => {},
                    onMessage: {addListener: () => {}},
                    id: 'ekdadkggalggkjgmnamaeidcdjnlajne'
                },
                loadTimes: function() {},
                csi: function() {},
                app: {isInstalled: false}
            };

            const makePlugin = (name, filename) => {
                const plugin = Object.create(Plugin.prototype);
                Object.defineProperties(plugin, {
                    name: {value: name},
                    filename: {value: filename},
                    length: {value: 1}
                });
                return plugin;
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [
                        makePlugin('Chrome PDF Plugin', 'internal-pdf-viewer'),
                        makePlugin('Chrome PDF Viewer', 'mhjfbmdgcfjbbpaeojofohoefgiehjai'),
                        makePlugin('Native Client', 'internal-nacl-plugin'),
                    ];
                    plugins.__proto__ = PluginArray.prototype;
                    return plugins;
                }
            });

            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'language',  {get: () => 'en-US'});
            Object.defineProperty(navigator, 'platform',  {get: () => 'Win32'});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});

            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalQuery(parameters)
            );

            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.apply(this, [parameter]);
            };

            Object.defineProperty(screen, 'availWidth',  {get: () => 1280});
            Object.defineProperty(screen, 'availHeight', {get: () => 800});
            Object.defineProperty(screen, 'colorDepth',  {get: () => 24});
            Object.defineProperty(screen, 'pixelDepth',  {get: () => 24});
        """)

    async def navigate(self, url: str) -> bool:
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                await self.page.goto(url, timeout=config.PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
                await self._human_delay()
                await self.human_mouse_move()
                return True
            except Exception as e:
                print(f"[Browser] Navigation attempt {attempt} failed: {e}")
                if attempt == config.MAX_RETRIES:
                    return False
                await asyncio.sleep(2)
        return False

    async def get_page_html(self) -> str:
        return await self.page.content()

    async def get_main_content_html(self) -> str:
        """
        Extract just the main content area of the page.
        Sends real HTML with real class names to LLM — no stripping.
        Tries common content selectors before falling back to full body.
        """
        for selector in ["main", "#main", ".main", "article", "#content", ".content", "#products", ".products", "body"]:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    html = await element.inner_html()
                    if len(html) > 500:
                        # Hard cap — keep tokens manageable
                        return html[:6000]
            except Exception:
                continue
        return (await self.page.content())[:6000]

    async def get_page_title(self) -> str:
        return await self.page.title()

    async def get_current_url(self) -> str:
        return self.page.url

    async def scroll_to_bottom(self):
        await self.page.evaluate("""
            () => new Promise(resolve => {
                let total = 0;
                const step = 300;
                const interval = setInterval(() => {
                    window.scrollBy(0, step);
                    total += step;
                    if (total >= document.body.scrollHeight) {
                        clearInterval(interval);
                        resolve();
                    }
                }, 120);
            })
        """)
        await self._human_delay()

    async def human_mouse_move(self):
        """Move mouse in a natural curve — looks less like a bot."""
        points = [
            (random.randint(100, 400), random.randint(100, 300)),
            (random.randint(400, 800), random.randint(200, 500)),
            (random.randint(200, 600), random.randint(300, 600)),
        ]
        for x, y in points:
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def click_element(self, selector: str) -> bool:
        try:
            await self.page.click(selector, timeout=5_000)
            await self._human_delay()
            return True
        except Exception:
            return False

    async def _human_delay(self):
        delay  = config.NAVIGATION_DELAY_MS / 1000
        jitter = random.uniform(0, 0.8)
        await asyncio.sleep(delay + jitter)

    async def close(self):
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            print(f"[Browser] Error during close: {e}")
