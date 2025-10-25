import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import httpx  # async HTTP client
import config
players = []

def insert_into_db(player):
	query = "INSERT IGNORE INTO `player_colors` (player, rankings_url, hexcode) VALUES (%s, %s, %s)"
	values = (player['real_name'], player['href'], player['color'])
	config.my_cursor.execute(query, values)
	config.cursor.commit()

async def main():
	base_url = "https://rankings.the-elite.net"
	url = f"{base_url}/players"

	async with async_playwright() as p, httpx.AsyncClient(timeout=10.0) as client:
		browser = await p.chromium.launch(headless=True)
		context = await browser.new_context()
		page = await context.new_page()

		await page.goto(url)
		await asyncio.sleep(10)  # wait for Cloudflare / JS

		html = await page.content()
		soup = BeautifulSoup(html, "html.parser")

		table = soup.find("table")
		if not table:
			print("Table not found!")
			await browser.close()
			return

		for tr in table.find_all("tr")[1:]:
			tds = tr.find_all("td")
			if len(tds) < 2:
				continue

			# First column href
			first_col = tds[0]
			link_tag = first_col.find("a")
			href = urljoin(base_url, link_tag["href"]) if link_tag else None

			# Second column text (real name)
			real_name = tds[1].get_text(strip=True)

			# Query API asynchronously
			api_url = f"https://rankings.the-elite.net/api/alpha/player?name={quote(real_name)}"
			try:
				r = await client.get(api_url)
				r.raise_for_status()
				data = r.json()
				color = data["players"][0].get("color") if data.get("players") else None
			except Exception as e:
				color = None
				print(f"Error fetching color for {real_name}: {e}")

			player_data = {
				"real_name": real_name.replace(" ", "_"),
				"href": href,
				"color": color
			}
			players.append(player_data)
			insert_into_db(player_data)

		await browser.close()

asyncio.run(main())
