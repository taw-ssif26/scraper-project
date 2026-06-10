import asyncio
from browser.engine import BrowserEngine
from browser.dom_cleaner import extract_html_skeleton

async def test():
    browser = BrowserEngine()
    await browser.launch()
    await browser.navigate("http://books.toscrape.com")
    await asyncio.sleep(2)
    raw_html = await browser.get_page_html()
    skeleton = extract_html_skeleton(raw_html)
    print(skeleton[:3000])
    await browser.close()

asyncio.run(test())
