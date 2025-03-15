import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def main():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://rankings.the-elite.net/history/" +  YEAR + "/" + MONTH)
        # Wait for the table or any element you expect
        await page.wait_for_selector("table", timeout=10000)
        html = await page.content()
        await browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find("table")
        if table is None:
            print("No table found!")
        else:
            a_tags = table.find_all("a")
            for a in a_tags:
                if "time" in a:
                    self.rankings_url = self.base_url + "/" + a.get("href"))

asyncio.run(main())
