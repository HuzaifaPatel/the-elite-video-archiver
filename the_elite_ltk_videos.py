import httplib2
from bs4 import BeautifulSoup, SoupStrainer
import time
import feedparser
import os
import youtube_dl
import requests # for def get_time_info():
from tqdm import tqdm
import refresh

#__________________________________________________________________________________________________
#SQL Connector
import mysql.connector

mydb = mysql.connector.connect(
	host = "localhost",
	user = "root",
	passwd = "",
	database = "the-elite-ltk-videos",
	)


my_cursor = mydb.cursor()


#__________________________________________________________________________________________________
#lists

rankings_url = [] 	#all urls on pr history page
filtered_url = [] 	#urls on pr history with video (filtered rankings url)
youtube_url  = [] 	#youtube video url
time_info    = [] 	#time info on rankings
rankings_id  = []   #rankings url id

#__________________________________________________________________________________________________
#filename lists

player = []
stage = []
difficulty = []
time_in_seconds = []
regular_time = []
game = []
filename = []
date_achieved = []
dead_url = []

#__________________________________________________________________________________________________

def get_time_url(year, month): #GETS ALL Times from www.rankings.the-elite.net/history/year/month
	
	pr_history = str(year) + "/" + str(month) #default value is 2001/10
	http = httplib2.Http()
	status, response = http.request('https://rankings.the-elite.net/ltk-history/' + pr_history)
	history = BeautifulSoup(response, 'html.parser')

	for proven_times in tqdm(history.find_all('a', href=True), desc = "Getting All Rankings URLS"):

		if 'perfect-dark/ltk/' in proven_times['href'] or 'goldeneye/ltk/' in proven_times['href']:
			rankings_url.append("https://rankings.the-elite.net" + proven_times['href'])
			time.sleep(0.05)

def remove_duplicates():

	global rankings_url
	temp_list = []

	for url in rankings_url: 
		if url not in temp_list: 
			temp_list.append(url) 	

	rankings_url.clear()

	for i in range(len(temp_list)):
		rankings_url.append(temp_list[i])

	rankings_url.reverse()
	temp_list.clear()


def get_yt_url():

	print("")

	for speedrun_with_video in tqdm(range(0,len(rankings_url)), desc = "Getting Youtube URLS"):

		http = httplib2.Http()
		status, response = http.request(rankings_url[speedrun_with_video])
		video = BeautifulSoup(response, 'html.parser')
		# time.sleep(.1)
		time.sleep(0.01)

		for yt_video in video.find_all('a', href=True):
			if 'youtube.com' in yt_video['href'] or 'twitch.tv/videos' in yt_video['href'] or 'activigor.com' in yt_video['href'] or 'thengamer.com/' in yt_video['href']:
				youtube_url.append(yt_video['href'])
				filtered_url.append(rankings_url[speedrun_with_video])
				#print("Found Video")

	#print("Got YouTube URL")
	print("")

def get_time_info():

	for proven_times in tqdm(range(0,len(filtered_url)), desc = "Getting Time Info"):

		request = requests.get(filtered_url[proven_times])
		html_content = request.text
		soup = BeautifulSoup(html_content, 'lxml')

		index_info = soup.find_all('title')[0]
		index_info = index_info.string
		index_info = index_info[:-21]
		time_info.append(index_info)

#________________________________________________________________________________________
#Code for getting date achieved. I made it in this function so i don't have to request the rankings so many times 

		date = soup.find_all(['li','strong'])#[51]
		date = str(date)
		date = date[date.find("<li><strong>Achieved:</strong>")+31:]
		date = date[0:date.find("</li>")]

		date = date.split()
		month = date[1]
		month = month[0:3]
		date[1] = month

		from datetime import datetime

		date = date[0] + "-" + date[1] + "-" + date[2] 
		date = datetime.strptime(date, '%d-%b-%Y')
		date = date.strftime("%Y-%m-%d")

		date_achieved.append(date)		

		time.sleep(0.05)

def get_rankings_url_id():

	for i in range(len(filtered_url)):
		rankings_url = filtered_url[i]
		rankings_url = rankings_url.split("/")
		ranking_id = int(rankings_url[len(rankings_url)-1])
		ranking_id = int(ranking_id)

		rankings_id.append(ranking_id)

def make_player_name():

	global player
	global stage

	for i in time_info:
		by = i.index("by")
		name = i[by+3:]
		name = name.replace(" ","_")
		player.append(name)

def make_difficulty_and_stage():

	global difficulty
	global stage

	for x in time_info:
		try:
			if x.index("Dark LTK"):
				difficulty.append("DLTK")
				checker = x.index("Dark LTK")
				get_stage = x
				get_stage = get_stage[0:checker-1]
				get_stage = get_stage.lower()
				stage.append(get_stage)
		except:
			try:
				if x.index("LTK"):
					difficulty.append("LTK")
					checker = x.index("LTK")
					get_stage = x
					get_stage = get_stage[0:checker-1]
					get_stage = get_stage.lower()
					stage.append(get_stage)
			except:
				pass

def make_time():

	for i in range(len(time_info)):
		x = time_info[i]
		x = x.index("LTK")
		x = x + 4

		c = time_info[i]
		c = c.index("by")
		c = c - 1

		f = time_info[i]
		f = f[x:c]
		# print(f)

		if f == "N/A": # if player submits a time = to 20:00
			# print("went thorugh")
			f = ("20:00")


		if f.count(":") == 2:
			h, m, s = f.split(":")
			time = (3600 * int(h)) + (int(m) * 60) + int(s)
		else:
			s = f.index(":")

			minute = f[0:s]
			minute = int(minute)
			minute = minute * 60
			
			seconds = f[s+1:]
			seconds = int(seconds)

			time = minute + seconds

		time = str(time)

		if len(time) == 3:
			time = "0" + time
		if len(time) == 2:
			time = "00" + time
		if len(time) == 1:
			time = "000" + time

		time_in_seconds.append(time)


def make_regular_time():
	import time
	
	for i in range(len(time_info)):

		seconds = time_in_seconds[i]
		
		if(seconds == "N/A"): # if player submits a time = to 20:00
			regular_time.append("20:00")
			continue

		reg_time = ""

		if int(time_in_seconds[i]) >= 3600:
			reg_time = time.strftime("%H:%M:%S", time.gmtime(int(time_in_seconds[i])))
		else:
			reg_time = time.strftime("%M:%S", time.gmtime(int(time_in_seconds[i])))


		reg_time = reg_time.split(":")

		for i in range(1):
			reg_time[0] = str(int(reg_time[0]))

		reg_time = ":".join(reg_time)
		regular_time.append(reg_time)


def make_game():

	global stage
	global game

	for i in range(len(time_info)):

		# G O L D E N E Y E 0 0 7

		if stage[i] in ("surface 1", "bunker 1", "surface 2", "bunker 2"):
			stage[i] = stage[i].replace(" ","")

		# P E R F E C T D A R K

		if stage[i] == "air force one":
			stage[i] = "af1"

		if stage[i] in ("air base", "crash site", "deep sea", "attack ship", "skedar ruins", "maian sos"):
			stage[i] = stage[i].replace(" ","-")

		if stage[i] == "pelagic ii":
			stage[i] = "pelagic"

		if stage[i] == "war!":
			stage[i] = "war"

		if stage[i] in ("dam", "facility", "runway", "surface1", 
						"bunker1", "silo", "frigate", "surface2", 
						"bunker2", "statue", "archives","streets", 
						"depot", "train", "jungle", "control", 
						"caverns", "cradle", "aztec", "egypt"):
			game.append("ge")

		if stage[i] in ("defection", "investigation", "extraction", 
						"villa", "chicago", "g5", "infiltration", 
						"rescue", "escape", "air-base","af1", 
						"crash-site", "pelagic", "deep-sea", "ci", 
						"attack-ship", "skedar-ruins", "mbr", 
						"maian-sos", "war", "duel"):
			game.append("pd")


def make_filename():


	for i in range(len(time_info)):

		new_filename = game[i] + "." + stage[i] + "." + difficulty[i] + "." + time_in_seconds[i] + "." + player[i] + ".mp4"
		filename.append(new_filename)


def make_folder():

	print("")
	print("Attempting to make directories... ")
	print("")

	for i in range(len(time_info)):
		
		try:
			#creates directory
			os.mkdir("D:\\Truth Saver RSS Backup\\the-elite-ltk-videos\\" + player[i])
			print("Directory ", player[i], " created")
			#print("")

		except:
			#print("Directory ", player[i], " already exists")
			#print("")
			continue

	print("_________________________________________")
	print("")


def get_player_dupes():

	updated_index = len(time_info) - 1

	for i in range(len(time_info)):
		# print(updated_index)
		temp_filename = filename[updated_index]

		my_cursor.execute("SELECT COUNT(*) FROM dupe_checker WHERE filename = (%s)", (filename[updated_index],))
		num_Of_Dupes = my_cursor.fetchall()[0][0]

		my_cursor.execute("SELECT COUNT(*) FROM video_data WHERE rankings_url = (%s)", (filtered_url[updated_index],))
		num_Of_rankings_url_duplicates = my_cursor.fetchall()[0][0]

		my_cursor.execute("SELECT COUNT(*) FROM video_data WHERE youtube_url = (%s)", (youtube_url[updated_index],))
		num_Of_youtube_url_duplicates = my_cursor.fetchall()[0][0]

		my_cursor.execute("SELECT COUNT(*) FROM video_data WHERE rankings_id = (%s)", (rankings_id[updated_index],))
		num_Of_rankings_id_duplicates = my_cursor.fetchall()[0][0]

		# print("youtube url: " + youtube_url[updated_index])
		# print("rankings url: " + filtered_url[updated_index])
		# print("filename: " + filename[updated_index])
		# print(num_Of_youtube_url_duplicates)
		# print(num_Of_rankings_url_duplicates)
		# print(num_Of_rankings_id_duplicates)
		# print(num_Of_Dupes)

		if num_Of_rankings_id_duplicates != 0:
			rankings_url.pop(updated_index)
			filtered_url.pop(updated_index)
			youtube_url.pop(updated_index)
			time_info.pop(updated_index)		
			player.pop(updated_index)
			stage.pop(updated_index)
			difficulty.pop(updated_index)
			time_in_seconds.pop(updated_index)
			game.pop(updated_index)
			filename.pop(updated_index)
			regular_time.pop(updated_index)
			date_achieved.pop(updated_index)
			rankings_id.pop(updated_index)
			updated_index = updated_index - 1
			continue


		if num_Of_Dupes > 0:
			temp_filename = filename[updated_index]
			new_filename = filename[updated_index]
			new_filename = new_filename[:-4]
			
			filename[updated_index] = str(new_filename) + "(" + str(num_Of_Dupes) + ").mp4"
			
		add_Filename = "INSERT INTO dupe_checker (filename, rankings_id) VALUES (%s, %s)"
		my_cursor.execute(add_Filename, (temp_filename, rankings_id[updated_index]))
		mydb.commit() #save

		updated_index = updated_index - 1

def download_video():

	global dead_url

	for i in range(len(time_info)):

		print("")
		print("Stage: " + stage[i])
		print("Player: " + player[i])
		print("Filename: " + filename[i])

		os.chdir("D:\\Truth Saver RSS Backup\\the-elite-ltk-videos\\" + player[i] + "\\")

		try:
			ydl_opts = {'outtmpl' : filename[i], 'noplaylist' : True}
			with youtube_dl.YoutubeDL(ydl_opts) as ydl:
				print("")
				ydl.download([youtube_url[i]])
				dead_url.append(0)
				print("")

		# except youtube_dl.utils.DownloadError:
		except:
			if youtube_url[i][0:22] == "https://www.twitch.tv/":
				print("")
				print("Twitch URL not valid. Contact The-Elite Proof Moderator or Historian")
				dead_url.append(1)
			elif youtube_url[i][0:24] == "http://www.thengamer.com":
				print("")
				print("Cannot download from thengamer.com")
				dead_url.append(1)
			elif youtube_url[i][0:25] == "http://www.activigor.com/":
				print("")
				print("Cannot download from activigor.com")
				dead_url.append(1)
			else:
				print("")
				print("YouTube URL not valid. Contact The-Elite Proof Moderator or Historian")
				dead_url.append(1)
				print("")


def update_database():

	addRow = "INSERT INTO video_data (game, stage, difficulty, time_in_seconds, regular_time, player, extension, youtube_url, published_date, rankings_url, filename, dead_youtube_url, rankings_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
	# print(len(game))
	# print(len(stage))
	# print(len(difficulty))
	# print(len(time_in_seconds))
	# print(len(regular_time))
	# print(len(player))
	# print(len(youtube_url))
	# print(len(date_achieved))
	# print(len(filtered_url))
	# print(len(filename))
	# print(len(dead_url))
	# print(len(rankings_id))
	for i in range(len(time_info)):
		record = (game[i], stage[i], difficulty[i], str(int(time_in_seconds[i])), regular_time[i], player[i], "mp4", youtube_url[i], date_achieved[i], filtered_url[i], filename[i], dead_url[i], rankings_id[i])
		my_cursor.execute(addRow, record)
		mydb.commit() #save

	print("")
	print("Finished. Added info to database")


#def set_database_counter():
	


def main():

	refresh.delete_LTK_Table()
	year = 2020
	month = "09"
	for i in range(1):
		print("")
		get_time_url(year, month)
		remove_duplicates()
		get_yt_url()
		get_time_info()
		get_rankings_url_id()
		make_player_name()
		make_difficulty_and_stage()
		make_time()
		make_regular_time()
		make_game()
		make_filename()
		make_folder()
		get_player_dupes()
		download_video()
		update_database()

		for i in range(len(time_info)):
			print(filename[i])

		rankings_url.clear()	#empties list
		filtered_url.clear()	
		youtube_url.clear()		
		time_info.clear()		
		player.clear()
		stage.clear()
		difficulty.clear()
		time_in_seconds.clear()
		game.clear()
		filename.clear()
		regular_time.clear()
		date_achieved.clear()
		dead_url.clear()
		rankings_id.clear()

		
		print("")
		if month == 12:
			year = year + 1
			month = 1
		else:
			month = month + 1
		# month = month + 1

		
main()