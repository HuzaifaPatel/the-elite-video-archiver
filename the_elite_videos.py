# 1997 DONE
# 1998 DONE
# 1999 DONE
# 2000 DONE
# 2001 DONE
# 2009 DONE
import httplib2
from bs4 import BeautifulSoup
import time
import os
import yt_dlp as youtube_dl
import requests
import urllib.request
from datetime import datetime
import config
import multiprocessing
import sys
from selenium.webdriver.chrome.options import Options
import tempfile
from selenium import webdriver
from urllib.parse import urlsplit, urlunsplit, quote

BASE_DIR = os.getcwd()
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
		self.get_rankings_url(YEAR, MONTH)

	# GET ALL TIMES FROM www.rankings.the-elite.net/history/year/month
	def get_rankings_url(self, YEAR, MONTH):
		options = Options()
		options.add_argument('--headless')
		user_data_dir = tempfile.mkdtemp()
		options.add_argument(f'--user-data-dir={user_data_dir}')
		driver = webdriver.Chrome(options=options)
		url = self.base_url + '/history/' + str(YEAR) + '/' + str(MONTH)
		driver.get(url)

		html = driver.page_source
		driver.quit()

		try:
			history = BeautifulSoup(html, 'lxml')
		except Exception as e:
			print(f"lxml parser failed: {e}. Falling back to html5lib.")
			history = BeautifulSoup(html, 'html5lib')


		for proven_time in history.find_all('a', href=True):
			if 'time' in proven_time['href']:
				# CHECK IF ALREADY IN DB..RIGHT AWAY. SAVE TIME.
				# if not
				# int(self.check_if_dupe(proven_time['href'].split("/")[-1])):
				self.rankings_url = self.base_url + proven_time['href']
				if self.has_video(self.rankings_url):
					self.rankings_id = proven_time['href'].split("/")[-1]
					self.get_time_info()
					self.make_game()
					self.make_filename()
					self.make_folder()
					self.download_video()
					self.upload_obj()
					self.update_database()

	def encode_url(self, url):
		parts = urlsplit(url)
		encoded_path = quote(parts.path, safe="/~")
		encoded_query = quote(parts.query, safe="=&?")
		return urlunsplit((parts.scheme, parts.netloc, encoded_path, encoded_query, parts.fragment))

	def parse_html(self, html):
		# This function will be run in a separate process.
		# Use html5lib to parse HTML.
		return BeautifulSoup(html, 'html5lib')

	def has_video(self, rankings_url):
		try:
			safe_url = self.encode_url(rankings_url)
			with urllib.request.urlopen(safe_url) as response:
				html = response.read().decode('utf-8', errors='replace')
			
			html = html.encode('utf-8', 'replace').decode('utf-8')
			
			# Use a separate process for parsing.
			with multiprocessing.Pool(1) as pool:
				# Apply the parse_html function with a timeout (e.g., 30 seconds)
				async_result = pool.apply_async(self.parse_html, (html,))
				try:
					soup = async_result.get(timeout=30)
				except multiprocessing.TimeoutError:
					print(f"Parsing timed out for {rankings_url}")
					return False
			
			# Look for an iframe with a YouTube embed.
			iframe = soup.find("iframe", src=lambda s: s and "youtube.com" in s)
			if iframe:
				embed_url = iframe.get("src")
				# Check if it's an embed URL and extract the video ID
				if "youtube.com/embed/" in embed_url:
					# Remove query parameters if any.
					base_url = embed_url.split('?')[0]
					video_id = base_url.split('/')[-1]
					# Construct the standard YouTube URL.
					youtube_url = f"https://www.youtube.com/watch?v={video_id}"
					print("YouTube video URL:", youtube_url)
					self.youtube_url = youtube_url
					return True
			
			return False

		except Exception as e:
			print(f"Error processing {rankings_url}: {e}")
			return False

		
	def get_time_info(self):
		request = requests.get(self.rankings_url)
		html_content = request.text
		soup = BeautifulSoup(html_content, 'html5lib')

		index_info = soup.find_all('title')[0].string[:-21]

		self.get_date(soup)
		self.get_name(index_info)
		self.get_difficulty(index_info)
		self.get_time_in_seconds(index_info)

	def get_date(self, soup):
		date = str(soup.find_all(['li', 'strong']))
		date = date[date.find("<li><strong>Achieved:</strong>") + 31:]
		date = date[0:date.find("</li>")].split()
		date = date[0] + "-" + date[1] + "-" + date[2]
		date = datetime.strptime(date, '%d-%B-%Y')
		date = date.strftime("%Y-%m-%d")

		self.date_achieved = date

	def get_name(self, index_info):
		by = index_info.index("by")
		name = index_info[by + 3:]
		name = name.replace(" ", "_")
		self.player = name

	def get_difficulty(self, index_info):
		if "Secret Agent" in index_info.split("by")[0]:
			self.difficulty = "SA"
			self.stage = index_info[0:index_info.index("Secret") - 1].lower()
		elif "Special Agent" in index_info.split("by")[0]:
			self.difficulty = "SA"
			self.stage = index_info[0:index_info.index("Special") - 1].lower()
		elif "00 Agent" in index_info.split("by")[0]:
			self.difficulty = "00A"
			self.stage = index_info[0:index_info.index("00") - 1].lower()
		elif "Perfect Agent" in index_info.split("by")[0]:
			self.difficulty = "PA"
			self.stage = index_info[0:index_info.index("Perfect") - 1].lower()
		else:
			self.difficulty = "Agent"
			self.stage = index_info[0:index_info.index("Agent") - 1].lower()

	def get_time_in_seconds(self, index_info):
		front_slice = index_info.index("Agent") + 6
		back_slice = index_info.index("by") - 1

		self.regular_time = index_info[front_slice:back_slice]

		time_in_seconds = None

		if self.regular_time == "N/A":  # if player submits a time = 20:00
			self.regular_time = "20:00"

		if self.regular_time.count(":") == 2:
			h, m, s = self.regular_time.split(":")
			time_in_seconds = (3600 * int(h)) + (int(m) * 60) + int(s)
		else:
			m, s = self.regular_time.split(":")
			time_in_seconds = str((int(m) * 60) + int(s))

		if len(time_in_seconds) == 3:
			time_in_seconds = "0" + time_in_seconds
		if len(time_in_seconds) == 2:
			time_in_seconds = "00" + time_in_seconds
		if len(time_in_seconds) == 1:
			time_in_seconds = "000" + time_in_seconds


		self.time_in_seconds = time_in_seconds
		# self.make_regular_time(time_in_seconds)

	def make_regular_time(self, _time):
		if (_time == "N/A"):  # if player submits a time = to 20:00
			self.regular_time = "20:00"
		elif int(_time) >= 3600:
			self.regular_time = time.strftime(
				"%H:%M:%S", time.gmtime(int(_time)))
		else:
			self.regular_time = time.strftime("%M:%S", time.gmtime(int(_time)))

	def make_game(self):
		# G O L D E N E Y E 0 0 7

		if self.stage in ("surface 1", "bunker 1", "surface 2", "bunker 2"):
			self.stage = self.stage.replace(" ", "")

		# P E R F E C T D A R K

		if self.stage == "air force one":
			self.stage = "af1"

		if self.stage in ("air base", "crash site", "deep sea",
						  "attack ship", "skedar ruins", "maian sos"):
			self.stage = self.stage.replace(" ", "-")

		if self.stage == "pelagic ii":
			self.stage = "pelagic"

		if self.stage == "war!":
			self.stage = "war"

		if self.stage in ("dam", "facility", "runway", "surface1",
						  "bunker1", "silo", "frigate", "surface2",
						  "bunker2", "statue", "archives", "streets",
						  "depot", "train", "jungle", "control",
						  "caverns", "cradle", "aztec", "egypt"):
			self.game = 'ge'

		if self.stage in ("defection", "investigation", "extraction",
						  "villa", "chicago", "g5", "infiltration",
						  "rescue", "escape", "air-base", "af1",
						  "crash-site", "pelagic", "deep-sea", "ci",
										"attack-ship", "skedar-ruins", "mbr",
										"maian-sos", "war", "duel"):
			self.game = 'pd'

	def make_filename(self):
		self.filename = self.game + "." + self.stage + "." + self.difficulty + \
			"." + self.time_in_seconds + "." + self.player + "." + self.rankings_id

	def make_folder(self):
		os.chdir(self.BASE_DIR)

		try:
			os.mkdir("the-elite-videos/" + self.player)
			print("Directory ", self.player, " created")
		except BaseException:
			pass

	def check_if_dupe(self, rank_id):
		config.my_cursor.execute(
			"SELECT COUNT(*) FROM `the-elite`.`the-elite-videos` WHERE rankings_id=(%s)",
			(rank_id,
			 ))
		return config.my_cursor.fetchall()[0][0]



	def key_exists(self):
		# Check if the file exists in DO Spaces
		try:
			key = f"{self.player}/{self.filename}"
			config.s3_client.head_object(Bucket=config.DO_SPACES_BUCKET, Key=key)
			print(f"File '{self.filename}' already exists in DO Spaces. Skipping download.")
			return True  # Exit early if file exists
		except config.s3_client.exceptions.ClientError as e:
			error_code = e.response.get("Error", {}).get("Code")
			if error_code != '404':
				print(f"Error checking if file exists in DO Spaces: {e}")
				return False
			# If error_code is '404', file does not exist; continue with download
		return False

	def download_video(self):
		print("")
		print("Rankings Url: " + self.rankings_url)
		print("Youtube_URL: " + self.youtube_url)
		print("Stage: " + self.stage)
		print("Player: " + self.player)
		print("Filename: " + self.filename)
		print("Date: " + self.date_achieved)
		print("Regular Time: " + self.regular_time)
		os.chdir(self.BASE_DIR + "/the-elite-videos/" + self.player)

		try:
			ydl_opts = {
				'outtmpl': self.filename + '.' + '%(ext)s',
				'noplaylist': True,
				'format': 'bestvideo+bestaudio/best',
				'quiet': True
			}

			with youtube_dl.YoutubeDL(ydl_opts) as ydl:
				print("")
				info_dict = ydl.extract_info(self.youtube_url, download=False)
				self.extension = info_dict.get('ext')
				self.filename = self.filename + "." + self.extension

			# DONT REMOVE THE ELSE STATEMENT. THE CODE WILL MAKE FILE_EXISTS = 1 AUTOMATICALLY. I DON'T KNOW WHY THIS HAPPENS.
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

		object_name = self.player + "/" + self.filename
		file_path = self.BASE_DIR + '/the-elite-videos/' + self.player + "/" + self.filename

		# First, check if the object already exists in the bucket
		try:
			config.s3_client.head_object(
				Bucket=config.DO_SPACES_BUCKET, Key=object_name)
			# If head_object doesn't raise an exception, the object exists.
			print(
				f"File '{object_name}' already exists in the bucket. Skipping upload.")
		except config.s3_client.exceptions.ClientError as e:
			error_code = e.response.get("Error", {}).get("Code")
			if error_code == '404':
				# Object does not exist; proceed with upload
				try:
					config.s3_client.upload_file(
						file_path,
						config.DO_SPACES_BUCKET,
						object_name,
						ExtraArgs={'ContentType': 'video/mp4', 'ACL': 'public-read'}
					)
					print(
						f"File '{file_path}' uploaded successfully as '{object_name}'.")
				except Exception as upload_error:
					print(f"Error uploading file '{file_path}':", upload_error)
			else:
				# An error occurred while checking if the object exists.
				print(f"Error checking if file exists '{object_name}':", e)

		try:
			os.remove(file_path)
			print(f"File '{file_path}' deleted successfully.")
		except OSError as delete_error:
			print(f"Error deleting file '{file_path}':", delete_error)

	def update_database(self):


		config.my_cursor.execute("SELECT * FROM `the-elite-videos` WHERE rankings_id = %s", (self.rankings_id,))
		row = config.my_cursor.fetchone()

		if row:
			print("Row exists. Updating...")
			# Prepare the update query to update all rows
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
				WHERE rankings_id = %s  # Update only the row with the specific rankings_id
			"""

			# Values to be updated (including the rankings_id as the identifier)
			values = (
				self.game,
				self.stage,
				self.difficulty,
				self.time_in_seconds,  # time_in_seconds
				self.regular_time,
				self.player,
				self.extension,
				self.youtube_url,
				self.date_achieved,  # published_date
				self.rankings_url,
				self.filename,
				self.dead_url,
				self.file_exists,  # file_exists (assuming 1 means it exists, 0 means it doesn't)
				self.rankings_id  # Use the rankings_id to target the row
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


# def main():
# 	if len(sys.argv) > 1:
# 		for MONTH in range(1, 13):
# 			Video(int(sys.argv[1]), MONTH)
# 			print("Month: " + str(MONTH))
# 	print(str(sys.argv) + " Complete")

def main():
	for YEAR in range(1997, 2025):
		for MONTH in range(1, 13):
			print("MONTH: " + str(MONTH) + " YEAR: " + str(YEAR))
			Video(YEAR, MONTH)
	print(str(sys.argv) + " Complete")

if __name__ == "__main__":
	main()
