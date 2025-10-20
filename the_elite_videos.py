#!/usr/bin/env python3
# the_elite_videos_playwright.py
# Replaces Selenium/undetected_chromedriver with Playwright for rendering & cookie-based verification.

# 1997 DONE
# 1998 DONE
# 1999 DONE
# 2000 DONE
# 2001 DONE
# 2009 DONE

import os
import sys
import time
import json
import pathlib
import multiprocessing
from datetime import datetime

import requests
import yt_dlp as youtube_dl
from bs4 import BeautifulSoup

# your config module must provide:
# - config.my_cursor (DB cursor)
# - config.cursor (DB connection with commit())
# - config.s3_client (boto3-compatible s3 client)
# - config.DO_SPACES_BUCKET (bucket name)
import config

# Playwright sync API
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Change this to a persistent location so solves stick between runs
PROFILE_DIR = os.path.expanduser("~/.elite_archiver_profile")
COOKIE_FILE = os.path.join(PROFILE_DIR, "cookies.json")
os.makedirs(PROFILE_DIR, exist_ok=True)

BASE_DIR = os.getcwd()

# ---------- Cookie helpers for Playwright ----------
def _load_cookies_from_file():
    if not os.path.exists(COOKIE_FILE) or os.path.getsize(COOKIE_FILE) == 0:
        return None
    try:
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
        return cookies
    except Exception:
        return None

def _save_cookies_to_file(cookies):
    try:
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f)
    except Exception as e:
        print("Failed to save cookies:", e)

# ---------- Playwright fetcher ----------
def fetch_with_playwright(url, timeout_ms=30000, headless=True, wait_for_selector="a[href*='time']"):
    """
    Fetch fully-rendered HTML for `url`.
    - Tries headless chromium first; if verification blocks headless, falls back to visible browser
      and prompts the user to solve verification manually. Cookies are saved to disk.
    """
    cookies_from_file = _load_cookies_from_file()

    with sync_playwright() as p:
        # Try headless first
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        if cookies_from_file:
            try:
                context.add_cookies(cookies_from_file)
            except Exception:
                # ignore cookie loading errors
                pass

        page = context.new_page()

        try:
            page.goto(url, timeout=timeout_ms)
        except Exception:
            # retry once more
            try:
                page.goto(url, timeout=timeout_ms)
            except Exception as e:
                print(f"Initial navigation failures: {e}")

        # Wait for either the real content selector OR a verification cookie then reload
        start = time.time()
        html = None
        try:
            while True:
                try:
                    if page.query_selector(wait_for_selector):
                        html = page.content()
                        break
                except Exception:
                    pass

                # Check cookies for verification markers
                try:
                    cookies = context.cookies()
                except Exception:
                    cookies = []

                # site-specific cookie check; adjust if needed
                if any(c.get("name", "").lower().startswith("verified") or c.get("name") == "verified-user" for c in cookies):
                    # reload to allow site to render protected content
                    try:
                        page.reload(timeout=timeout_ms)
                    except Exception:
                        pass
                    try:
                        if page.wait_for_selector(wait_for_selector, timeout=5000):
                            html = page.content()
                            break
                    except PlaywrightTimeoutError:
                        pass

                elapsed_ms = (time.time() - start) * 1000
                if elapsed_ms > timeout_ms:
                    # timed out — return what we have (could be the checking page)
                    html = page.content()
                    break
                time.sleep(0.4)
        except PlaywrightTimeoutError:
            html = page.content()

        # Save cookies to disk for future runs
        try:
            saved_cookies = context.cookies()
            _save_cookies_to_file(saved_cookies)
        except Exception:
            pass

        browser.close()

        # If headless failed and returned the verification page, open visible browser for manual solve
        if headless and html and ("Checking your browser" in html or "Verifying your connection" in html) and not page.query_selector(wait_for_selector):
            print("Headless run returned verification page. Launching visible browser for manual verification...")
            browser2 = p.chromium.launch(headless=False)
            context2 = browser2.new_context()
            if cookies_from_file:
                try:
                    context2.add_cookies(cookies_from_file)
                except Exception:
                    pass
            page2 = context2.new_page()
            page2.goto(url, timeout=60000)
            print("Please complete any verification in the opened browser window. After verifying, press Enter here to continue...")
            input()
            # Save new cookies and capture content
            try:
                saved_cookies2 = context2.cookies()
                _save_cookies_to_file(saved_cookies2)
            except Exception:
                pass
            try:
                page2.wait_for_selector(wait_for_selector, timeout=30000)
            except Exception:
                pass
            html = page2.content()
            browser2.close()

        return html

# ---------- Utility helpers ----------
def encode_url(url):
    from urllib.parse import urlsplit, urlunsplit, quote
    parts = urlsplit(url)
    encoded_path = quote(parts.path, safe="/~")
    encoded_query = quote(parts.query, safe="=&?")
    return urlunsplit((parts.scheme, parts.netloc, encoded_path, encoded_query, parts.fragment))

# ---------- Main Video class (adapted) ----------
class Video:
    def __init__(self, YEAR, MONTH):
        self.base_url = "https://rankings.the-elite.net"
        self.rankings_url = None
        self.rankings_id = None
        self.youtube_url = None
        self.player = None
        self.stage = None
        self.difficulty = None
        self.time_in_seconds = None
        self.regular_time = None
        self.game = None
        self.filename = None
        self.date_achieved = None
        self.dead_url = 0
        self.extension = None
        self.file_exists = None
        self.BASE_DIR = BASE_DIR

        # Kick off
        self.get_rankings_url(YEAR, MONTH)

    # GET ALL TIMES FROM /history/year/month using Playwright
    def get_rankings_url(self, YEAR, MONTH, interactive_on_fail=True):
        url = f"{self.base_url}/history/{YEAR}/{MONTH}"
        print(f"Fetching month page: {url}")
        html = fetch_with_playwright(url, headless=True, timeout_ms=30000)
        if not html:
            print("Failed to fetch month page or got empty HTML.")
            return

        history = BeautifulSoup(html, "lxml")

        for proven_time in history.find_all("a", href=True):
            href = proven_time["href"]
            if "time" not in href:
                continue

            self.rankings_url = self.base_url + href

            # fetch the individual ranking page and check for embedded YouTube
            ranking_html = fetch_with_playwright(self.rankings_url, headless=True, timeout_ms=30000)
            if not ranking_html:
                print("Failed fetching ranking page:", self.rankings_url)
                continue

            # parse ranking page to find iframe
            soup = BeautifulSoup(ranking_html, "lxml")
            iframe = soup.find("iframe", src=lambda s: s and "youtube.com/embed/" in s)
            if not iframe:
                # no iframe found
                continue

            embed_url = iframe.get("src")
            base_url = embed_url.split("?")[0]
            video_id = base_url.split("/")[-1]
            self.youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            print("YouTube video URL:", self.youtube_url)

            # populate fields from the ranking page HTML
            try:
                self.rankings_id = href.split("/")[-1]
                # use get_time_info with html_content provided
                self.get_time_info(html_content=ranking_html)
                self.make_game()
                self.make_filename()
                self.make_folder()

                # skip download/upload if file already exists in bucket
                if self.key_exists():
                    self.file_exists = 1
                else:
                    self.file_exists = 0
                    self.download_video()
                    if not self.file_exists:
                        self.upload_obj()
                self.update_database()
            except Exception as e:
                print("Error processing ranking:", e)
                continue

    # parse HTML in separate process if you want (keeps your design)
    def parse_html(self, html):
        return BeautifulSoup(html, "html5lib")

    def get_time_info(self, html_content=None, retries=3):
        """
        If html_content is provided, parse it. Otherwise fallback to requests (not preferred).
        """
        if html_content is None:
            # fallback (not JS-rendered)
            html_content = requests.get(self.rankings_url).text

        soup = BeautifulSoup(html_content, "html5lib")

        # title contains something like "<stage> Agent ... by <player>" — original logic used [:-21]
        title_tags = soup.find_all("title")
        if not title_tags:
            raise RuntimeError("No <title> found on ranking page.")
        index_info = title_tags[0].string
        if index_info is None:
            raise RuntimeError("Title string is empty.")
        # original code trimmed off trailing suffix; mimic that
        if len(index_info) > 21:
            index_info = index_info[:-21]
        else:
            # use as-is if shorter
            index_info = index_info

        self.get_date(soup)
        self.get_name(index_info)
        self.get_difficulty(index_info)
        self.get_time_in_seconds(index_info)

    def get_date(self, soup):
        # robust extraction: look for <li><strong>Achieved:</strong> ...</li>
        achieved_li = None
        for li in soup.find_all("li"):
            strong = li.find("strong")
            if strong and "Achieved" in strong.get_text():
                achieved_li = li.get_text()
                break
        if not achieved_li:
            # fallback: brute force original approach
            date_str = str(soup.find_all(["li", "strong"]))
            if "<li><strong>Achieved:</strong>" in date_str:
                date = date_str[date_str.find("<li><strong>Achieved:</strong>") + 31:]
                date = date[0:date.find("</li>")].split()
                date = date[0] + "-" + date[1] + "-" + date[2]
                date = datetime.strptime(date, "%d-%B-%Y")
                date = date.strftime("%Y-%m-%d")
                self.date_achieved = date
                return
            else:
                # last resort
                self.date_achieved = datetime.utcnow().strftime("%Y-%m-%d")
                return

        # achieved_li contains full li text. Extract date words after 'Achieved:'
        try:
            parts = achieved_li.split("Achieved:")[-1].strip()
            # expected like "6 June 2024" or "06 June 2024"
            date_parts = parts.split()[:3]
            date_str = " ".join(date_parts)
            date = datetime.strptime(date_str, "%d %B %Y")
            self.date_achieved = date.strftime("%Y-%m-%d")
        except Exception:
            # fallback to today
            self.date_achieved = datetime.utcnow().strftime("%Y-%m-%d")

    def get_name(self, index_info):
        # original logic: find 'by' and take the name after it
        if "by" in index_info:
            by = index_info.index("by")
            name = index_info[by + 3 :]
            name = name.replace(" ", "_")
            self.player = name
        else:
            self.player = "unknown_player"

    def get_difficulty(self, index_info):
        left = index_info.split("by")[0]
        if "Secret Agent" in left:
            self.difficulty = "SA"
            self.stage = left[0 : left.index("Secret") - 1].lower()
        elif "Special Agent" in left:
            self.difficulty = "SA"
            self.stage = left[0 : left.index("Special") - 1].lower()
        elif "00 Agent" in left:
            self.difficulty = "00A"
            self.stage = left[0 : left.index("00") - 1].lower()
        elif "Perfect Agent" in left:
            self.difficulty = "PA"
            self.stage = left[0 : left.index("Perfect") - 1].lower()
        else:
            if "Agent" in left:
                self.difficulty = "Agent"
                self.stage = left[0 : left.index("Agent") - 1].lower()
            else:
                self.difficulty = "Agent"
                self.stage = left.strip().lower()

    def get_time_in_seconds(self, index_info):
        # original logic uses the 'Agent' word to slice out the time
        if "Agent" in index_info and "by" in index_info:
            try:
                front_slice = index_info.index("Agent") + 6
                back_slice = index_info.index("by") - 1
                self.regular_time = index_info[front_slice:back_slice].strip()
            except Exception:
                self.regular_time = "0:00"
        else:
            self.regular_time = "0:00"

        if self.regular_time == "N/A":
            self.regular_time = "20:00"

        if self.regular_time.count(":") == 2:
            h, m, s = self.regular_time.split(":")
            time_in_seconds = (3600 * int(h)) + (int(m) * 60) + int(s)
        else:
            try:
                m, s = self.regular_time.split(":")
                time_in_seconds = (int(m) * 60) + int(s)
            except Exception:
                time_in_seconds = 0

        time_in_seconds = str(int(time_in_seconds))

        # pad to 4 digits like original code did
        while len(time_in_seconds) < 4:
            time_in_seconds = "0" + time_in_seconds

        self.time_in_seconds = time_in_seconds

    def make_game(self):
        # normalise stage names to game code
        if self.stage in ("surface 1", "bunker 1", "surface 2", "bunker 2"):
            self.stage = self.stage.replace(" ", "")
        if self.stage == "air force one":
            self.stage = "af1"
        if self.stage in ("air base", "crash site", "deep sea", "attack ship", "skedar ruins", "maian sos"):
            self.stage = self.stage.replace(" ", "-")
        if self.stage == "pelagic ii":
            self.stage = "pelagic"
        if self.stage == "war!":
            self.stage = "war"

        if self.stage in ("dam", "facility", "runway", "surface1", "bunker1", "silo", "frigate", "surface2", "bunker2",
                          "statue", "archives", "streets", "depot", "train", "jungle", "control", "caverns", "cradle", "aztec", "egypt"):
            self.game = "ge"

        if self.stage in ("defection", "investigation", "extraction", "villa", "chicago", "g5", "infiltration", "rescue",
                          "escape", "air-base", "af1", "crash-site", "pelagic", "deep-sea", "ci", "attack-ship", "skedar-ruins",
                          "mbr", "maian-sos", "war", "duel"):
            self.game = "pd"

    def make_filename(self):
        self.filename = f"{self.game}.{self.stage}.{self.difficulty}.{self.time_in_seconds}.{self.player}.{self.rankings_id}"

    def make_folder(self):
        os.chdir(self.BASE_DIR)
        try:
            os.makedirs(os.path.join("the-elite-videos", self.player), exist_ok=True)
            # print("Directory ", self.player, " created")
        except Exception:
            pass

    def check_if_dupe(self, rank_id):
        config.my_cursor.execute(
            "SELECT COUNT(*) FROM `the-elite`.`the-elite-videos` WHERE rankings_id=(%s)",
            (rank_id,)
        )
        return config.my_cursor.fetchall()[0][0]

    def key_exists(self):
        # Check if the file exists in DO Spaces
        try:
            key = f"{self.player}/{self.filename}"
            config.s3_client.head_object(Bucket=config.DO_SPACES_BUCKET, Key=key)
            print(f"File '{self.filename}' already exists in DO Spaces. Skipping download.")
            return True  # Exit early if file exists
        except Exception as e:
            # If the head_object fails, continue with download
            # For boto3 ClientError you'd inspect e.response but keep this broad for portability
            return False

    def download_video(self):
        print("")
        print("Rankings Url: " + str(self.rankings_url))
        print("Youtube_URL: " + str(self.youtube_url))
        print("Stage: " + str(self.stage))
        print("Player: " + str(self.player))
        print("Filename: " + str(self.filename))
        print("Date: " + str(self.date_achieved))
        print("Regular Time: " + str(self.regular_time))

        os.chdir(os.path.join(self.BASE_DIR, "the-elite-videos", self.player))

        try:
            ydl_opts = {
                "outtmpl": self.filename + "." + "%(ext)s",
                "noplaylist": True,
                "format": "bestvideo+bestaudio/best",
                "quiet": True,
                "cookiefile": "cookies.txt"
            }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                print("")
                info_dict = ydl.extract_info(self.youtube_url, download=False)
                self.extension = info_dict.get("ext")
                self.filename = self.filename + "." + self.extension

            if self.key_exists():
                self.file_exists = 1
                return
            else:
                self.file_exists = 0

            print("Downloaded file extension:", self.extension)
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(self.youtube_url, download=True)
        except youtube_dl.utils.ExtractorError as e:
            print(f"Error: {str(e)}")
            self.dead_url = 1
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            self.dead_url = 1

    def upload_obj(self):
        if self.file_exists:
            return

        object_name = f"{self.player}/{self.filename}"
        file_path = os.path.join(self.BASE_DIR, "the-elite-videos", self.player, self.filename)

        # First, check if the object already exists in the bucket
        try:
            config.s3_client.head_object(Bucket=config.DO_SPACES_BUCKET, Key=object_name)
            print(f"File '{object_name}' already exists in the bucket. Skipping upload.")
        except Exception as e:
            # proceed to upload
            try:
                config.s3_client.upload_file(
                    file_path,
                    config.DO_SPACES_BUCKET,
                    object_name,
                    ExtraArgs={"ContentType": "video/mp4", "ACL": "public-read"}
                )
                print(f"File '{file_path}' uploaded successfully as '{object_name}'.")
            except Exception as upload_error:
                print(f"Error uploading file '{file_path}':", upload_error)

        try:
            os.remove(file_path)
            print(f"File '{file_path}' deleted successfully.")
        except OSError as delete_error:
            print(f"Error deleting file '{file_path}':", delete_error)

    def update_database(self):
        try:
            config.my_cursor.execute("SELECT * FROM `the-elite-videos` WHERE rankings_id = %s", (self.rankings_id,))
            row = config.my_cursor.fetchone()

            if row:
                print("Row exists. Updating...")
                update_query = """
                    UPDATE `the-elite-videos`
                    SET 
                        game = %s,
                        stage = %s,
                        difficulty = %s,
                        time_in_seconds = %s,
                        regular_time = %s,
                        player = %s,
                        extension = %s,
                        youtube_url = %s,
                        published_date = %s,
                        rankings_url = %s,
                        filename = %s,
                        dead_youtube_url = %s,
                        file_exists = %s
                    WHERE rankings_id = %s
                """
                values = (
                    self.game,
                    self.stage,
                    self.difficulty,
                    self.time_in_seconds,
                    self.regular_time,
                    self.player,
                    self.extension,
                    self.youtube_url,
                    self.date_achieved,
                    self.rankings_url,
                    self.filename,
                    self.dead_url,
                    self.file_exists,
                    self.rankings_id
                )
                config.my_cursor.execute(update_query, values)
                config.cursor.commit()
                print(f"{config.my_cursor.rowcount} row(s) updated successfully.")
            else:
                print("Row does not exist. Inserting new row...")
                addRow = "INSERT INTO `the-elite`.`the-elite-videos` (game, stage, difficulty, time_in_seconds, regular_time, player, extension, youtube_url, published_date, rankings_url, filename, dead_youtube_url, rankings_id, file_exists) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                record = (
                    self.game, self.stage, self.difficulty, self.time_in_seconds, self.regular_time, self.player, self.extension,
                    self.youtube_url, self.date_achieved, self.rankings_url, self.filename, self.dead_url, self.rankings_id, self.file_exists
                )
                config.my_cursor.execute(addRow, record)
                config.cursor.commit()
                print(f"{config.my_cursor.rowcount} row(s) added successfully.")
        except Exception as e:
            print("Database update error:", e)

    def debug(self):
        print("")
        print(f"rankings_url: {self.rankings_url}")
        print(f"rankings_id: {self.rankings_id}")
        print(f"youtube_url: {self.youtube_url}")
        print(f"player: {self.player}")
        print(f"stage: {self.stage}")
        print(f"difficulty: {self.difficulty}")
        print(f"time_in_seconds: {self.time_in_seconds}")
        print(f"regular_time: {self.regular_time}")
        print(f"game: {self.game}")
        print(f"filename: {self.filename}")
        print(f"date_achieved: {self.date_achieved}")
        print(f"dead_url: {self.dead_url}")
        print(f"extension: {self.extension}")
        print("")

# ---------- CLI entrypoint ----------
def main():
    if len(sys.argv) > 1:
        year = int(sys.argv[1])
        # you previously iterated months 6..12; keep same unless you want all
        for MONTH in range(6, 13):
            try:
                print(f"Processing YEAR {year} MONTH {MONTH}")
                Video(year, MONTH)
            except Exception as e:
                print(f"Error processing {year}-{MONTH}: {e}")
    else:
        print("Usage: python3 the_elite_videos_playwright.py <YEAR>")

    print(str(sys.argv) + " Complete")

if __name__ == "__main__":
    main()
