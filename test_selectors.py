import asyncio
from browser.engine import BrowserEngine

async def test():
    browser = BrowserEngine()
    await browser.launch()
    await browser.navigate("http://books.toscrape.com")
    await asyncio.sleep(2)
    
    selectors = [
        "article.product_pod h3 a",
        "article.product_pod p.price_color",
        "article h3 a",
        "h3 a",
        ".product_pod h3 a",
        "p.price_color",
    ]
    
    for sel in selectors:
        elements = await browser.page.query_selector_all(sel)
        print(f"{sel}: {len(elements)} elements found")
    
    await browser.close()

asyncio.run(test())
