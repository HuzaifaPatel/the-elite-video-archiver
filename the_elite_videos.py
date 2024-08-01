import httplib2
from bs4 import BeautifulSoup, SoupStrainer
import time
import os
import yt_dlp as youtube_dl
import requests
from datetime import datetime
import config
import threading
import sys


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
		self.dead_url = None
		self.extension = None
		self.file_exists = None
		self.get_rankings_url(YEAR, MONTH)



	def get_rankings_url(self, YEAR, MONTH): # GET ALL TIMES FROM www.rankings.the-elite.net/history/year/month
		rankings_url = []
		http = httplib2.Http()
		status, response = http.request(self.base_url + '/history/' +str(YEAR) + '/' + str(MONTH))
		history = BeautifulSoup(response, 'html.parser')

		for proven_time in history.find_all('a', href=True):
			if 'time' in proven_time['href']:
				if not int(self.check_if_dupe(proven_time['href'].split("/")[-1])): # CHECK IF ALREADY IN DB..RIGHT AWAY. SAVE TIME.
					if self.has_video(self.base_url + proven_time['href']):
						self.rankings_url = self.base_url + proven_time['href']
						self.rankings_id = proven_time['href'].split("/")[-1]
						self.get_time_info()
						self.make_game()
						self.make_filename()
						self.make_folder()
						self.download_video()
						self.get_extension()
						# self.insert_file()
						self.update_database()



	def has_video(self, rankings_url):
		http = httplib2.Http()
		status, response = http.request(rankings_url)
		video = BeautifulSoup(response, 'html.parser')

		for a_tag in video.find_all('a', href=True):
			if 'youtube.com' in a_tag['href'] or 'twitch.tv/videos' in a_tag['href'] or 'activigor.com' in a_tag['href'] or 'thengamer.com' in a_tag['href']:
				self.youtube_url = a_tag['href']
				return True;
		return False;



	def get_time_info(self):
			request = requests.get(self.rankings_url)
			html_content = request.text
			soup = BeautifulSoup(html_content, 'lxml')
	
			index_info = soup.find_all('title')[0].string[:-21]

			self.get_date(soup)
			self.get_name(index_info)
			self.get_difficulty(index_info)
			self.get_time_in_seconds(index_info)



	def get_date(self, soup):
		date = str(soup.find_all(['li','strong']))
		date = date[date.find("<li><strong>Achieved:</strong>")+31:]
		date = date[0:date.find("</li>")].split()
		date = date[0] + "-" + date[1] + "-" + date[2] 
		date = datetime.strptime(date, '%d-%B-%Y')
		date = date.strftime("%Y-%m-%d")

		self.date_achieved = date



	def get_name(self, index_info):	
		by = index_info.index("by")
		name = index_info[by+3:]
		name = name.replace(" ","_")
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

		regular_time = index_info[front_slice:back_slice]
		time_in_seconds = None

		if regular_time == "N/A": # if player submits a time = 20:00
			regular_time = "20:00"

		if regular_time.count(":") == 2:
			h, m, s = regular_time.split(":")
			time_in_seconds = (3600 * int(h)) + (int(m) * 60) + int(s)
		else:
			m,s = regular_time.split(":")
			time_in_seconds = str((int(m) * 60) + int(s))

		if len(regular_time) == 3:
			regular_time = "0" + regular_time
		if len(regular_time) == 2:
			regular_time = "00" + regular_time
		if len(regular_time) == 1:
			regular_time = "000" + regular_time

		self.time_in_seconds = time_in_seconds
		self.make_regular_time(time_in_seconds)




	def make_regular_time(self, _time):
		if(_time == "N/A"): # if player submits a time = to 20:00
			self.regular_time = "20:00"
		elif int(_time) >= 3600:
			self.regular_time = time.strftime("%H:%M:%S", time.gmtime(int(_time)))
		else:
			self.regular_time = time.strftime("%M:%S", time.gmtime(int(_time)))



	def make_game(self):
		# G O L D E N E Y E 0 0 7

		if self.stage in ("surface 1", "bunker 1", "surface 2", "bunker 2"):
			self.stage = self.stage.replace(" ", "")

		# P E R F E C T D A R K

		if self.stage == "air force one":
			self.stage = "af1"

		if self.stage in ("air base", "crash site", "deep sea", "attack ship", "skedar ruins", "maian sos"):
			self.stage = self.stage.replace(" ", "-")

		if self.stage == "pelagic ii":
			self.stage = "pelagic"

		if self.stage == "war!":
			self.stage = "war"

		if self.stage in ("dam", "facility", "runway", "surface1", 
						"bunker1", "silo", "frigate", "surface2", 
						"bunker2", "statue", "archives","streets", 
						"depot", "train", "jungle", "control", 
						"caverns", "cradle", "aztec", "egypt"):
			self.game = 'ge'

		if self.stage in ("defection", "investigation", "extraction", 
						"villa", "chicago", "g5", "infiltration", 
						"rescue", "escape", "air-base","af1", 
						"crash-site", "pelagic", "deep-sea", "ci", 
						"attack-ship", "skedar-ruins", "mbr", 
						"maian-sos", "war", "duel"):
			self.game = 'pd'




	def make_filename(self):
		self.filename = self.game + "." + self.stage + "." + self.difficulty + "." + self.time_in_seconds + "." + self.player + "." + self.rankings_id



	def make_folder(self):
		os.chdir("/home/huzi/Projects/the-elite-videos-master/versions/V 3.0")

		try:
			os.mkdir("the-elite-videos/" + self.player)
			print("Directory ", self.player, " created")
		except:
			pass



	def check_if_dupe(self, rank_id):
		config.my_cursor.execute("SELECT COUNT(*) FROM `the-elite`.`the-elite-videos` WHERE rankings_id=(%s)", (rank_id,))
		return config.my_cursor.fetchall()[0][0]



	def download_video(self):
		print("")
		print("Stage: " + self.stage)
		print("Player: " + self.player)
		print("Filename: " + self.filename)
		print("Date: " + self.date_achieved)

		os.chdir("the-elite-videos/" + self.player + "/")

		try:
			ydl_opts = {'outtmpl' : self.filename + '.' + '%(ext)s', 'noplaylist' : True, 'format' : 'bestvideo+bestaudio/best'}

			with youtube_dl.YoutubeDL(ydl_opts) as ydl:
				print("")
				ydl.download([self.youtube_url])
				self.dead_url = 0
				self.file_exists = 1
				print("")
		except:
			self.dead_url = 1
			self.file_exists = 0



	def get_extension(self):
		if os.path.isfile(self.filename + '.mkv'):
		    self.extension = '.mkv'
		elif os.path.isfile(self.filename + '.mp4'):
		    self.extension = '.mp4'
		elif os.path.isfile(self.filename + '.webm'):
		    self.extension = '.webm'
		elif os.path.isfile(self.filename + '.mov'):
		    self.extension = '.mov'
		elif os.path.isfile(self.filename + '.avi'):
		    self.extension = '.avi'
		elif os.path.isfile(self.filename + '.mpeg'):
		    self.extension = '.mpeg'
		elif os.path.isfile(self.filename + '.mpg'):
		    self.extension = '.mpg'



	def insert_file(self):
		try:
			config.client.upload_file(self.filename + self.extension, 'huzi', self.player + "/" + self.filename + self.extension)
			dead_url[i] = 0
			print("FILE UPLOADED")
		except:
			pass


	def update_database(self):

		addRow = "INSERT INTO `the-elite`.`the-elite-videos` (game, stage, difficulty, time_in_seconds, regular_time, player, extension, youtube_url, published_date, rankings_url, filename, dead_youtube_url, rankings_id, file_exists) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

		record = (	
					self.game, self.stage, self.difficulty, self.time_in_seconds, self.regular_time, self.player, self.extension,
					self.youtube_url, self.date_achieved, self.rankings_url, self.filename, self.dead_url, self.rankings_id, self.file_exists
				)

		config.my_cursor.execute(addRow, record)
		config.mydb.commit() #save

		print("")
		print("Finished. Added info to database")
		print("")



def main():
	if len(sys.argv) > 1:
		for MONTH in range(1,13):
			Video(int(sys.argv[1]), MONTH)

if __name__ == "__main__":
	main()
