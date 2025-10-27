#!/usr/bin/env python3
# scrape_elite_videos_playwright.py

import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://rankings.the-elite.net"

def fetch_html(url, headless=True, timeout_ms=30000):
    """Fetch fully-rendered HTML using Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            page.goto(url, timeout=timeout_ms)
            # wait for the table rows to appear
            page.wait_for_selector("table.history-table tr", timeout=timeout_ms)
            time.sleep(1)  # give extra time for JS rendering
            html = page.content()
        except PlaywrightTimeoutError:
            print(f"Timeout loading page: {url}")
            html = page.content()
        finally:
            browser.close()
        return html

def convert_embed_to_watch_url(embed_url):
    """Convert YouTube embed URL to regular watch URL."""
    if "embed/" in embed_url:
        video_id = embed_url.split("/embed/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={video_id}"
    return embed_url

def scrape_month(year, month):
    url = f"{BASE_URL}/history/{year}/{month}"
    print(f"Scraping {year}-{month} at {url}")
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    videos = []

    # look for all <a> elements in the table
    for a in soup.select("table.history-table a"):
        href = a.get("href")
        if not href:
            continue

        youtube_url = None
        rankings_url = None

        # Direct YouTube link
        if "youtube.com" in href:
            youtube_url = href
            rankings_url = None

        # Overlay page links
        elif "javascript:Site.openOverlay" in a.get("onclick", ""):
            # extract overlay path
            onclick = a["onclick"]
            start = onclick.find("('") + 2
            end = onclick.find("')", start)
            overlay_path = onclick[start:end]
            overlay_url = urljoin(BASE_URL, overlay_path)
            rankings_url = overlay_url.replace("/video/", "/")

            # fetch overlay page to find YouTube iframe
            overlay_html = fetch_html(overlay_url)
            if overlay_html:
                overlay_soup = BeautifulSoup(overlay_html, "lxml")
                iframe = overlay_soup.find("iframe", src=lambda s: s and "youtube.com/embed/" in s)
                if iframe:
                    youtube_url = convert_embed_to_watch_url(iframe.get("src"))

        if youtube_url:
            videos.append({
                "youtube_url": youtube_url,
                "rankings_url": rankings_url
            })

    print(f"  Found {len(videos)} videos")
    return videos

def scrape_year(year):
    all_videos = []
    for month in range(5, 13):
        month_videos = scrape_month(year, month)
        all_videos.extend(month_videos)
    return all_videos

if __name__ == "__main__":
    YEAR = 1998
    videos = scrape_year(YEAR)
    for v in videos:
        print(f"YouTube: {v['youtube_url']}, Rankings: {v['rankings_url']}")
    print(f"Total videos found: {len(videos)}")
