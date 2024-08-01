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
	database = "the-elite-single-segment-videos",
)


my_cursor = mydb.cursor()


#__________________________________________________________________________________________________
#lists

rankings_url = [] 	#all urls on pr history page
youtube_url  = [] 	#youtube video url
time_info    = [] 	#time info on rankings
rankings_id  = []   #rankings url id

#__________________________________________________________________________________________________
#filename lists

player = []
category = []
time_in_seconds = []
regular_time = []
game = []
filename = []
date_achieved = []
dead_url = []
time_type = []
make_time_helper = []

#__________________________________________________________________________________________________

def get_yt_url(counter): #GETS ALL Times from www.rankings.the-elite.net/history/year/month
	url = 'https://rankings.the-elite.net/goldeneye/single-segments/' + str(counter)
	http = httplib2.Http()
	status, response = http.request('https://rankings.the-elite.net/goldeneye/single-segments/' + str(counter))
	video = BeautifulSoup(response, 'html.parser')

	for yt_video in video.find_all('a', href=True):
		if 'youtube.com' in yt_video['href'] or 'twitch.tv/videos' in yt_video['href'] or 'activigor.com' in yt_video['href'] or 'thengamer.com/' in yt_video['href']:
			youtube_url.append(yt_video['href'])
			rankings_url.append(url)

def remove_duplicates():

	global rankings_url
	final_list = []

	for url in rankings_url: 
		if url not in final_list: 
			final_list.append(url) 	

	rankings_url.clear()

	for i in range(len(final_list)):
		rankings_url.append(final_list[i])

	rankings_url.reverse()


def get_time_info():

	for proven_times in range(0,len(rankings_url)):

		request = requests.get(rankings_url[proven_times])
		html_content = request.text
		soup = BeautifulSoup(html_content, 'lxml')

		index_info = soup.find_all('title')[0]
		index_info = index_info.string
		index_info = index_info[:-21]
		time_info.append(index_info)

#________________________________________________________________________________________
#Code for getting date achieved. I made it in this function so i don't have to request the rankings so many times 
		try:
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
		except ValueError:	
			date_achieved.append("Unknown")

		rta_type = soup.find_all(['li','strong'])#[51]
		rta_type = str(rta_type)
		rta_type = rta_type[rta_type.find("<li><strong>Type:</strong>")+27:]
		rta_type = rta_type[0:rta_type.find("</li>")]
		time_type.append(rta_type)
		
		time.sleep(0.05)

def get_rankings_url_id():

	for i in range(len(rankings_url)):
		url = rankings_url[i]
		url = url.split("/")
		ranking_id = int(url[len(url)-1])
		ranking_id = int(ranking_id)

		rankings_id.append(ranking_id)


def make_player_name():

	global player

	for i in time_info:
		by = i.index("by")
		name = i[by+3:]
		name = name.replace(" ","_")
		player.append(name)


def make_category():

	global category

	for x in time_info:
		try:
			if x.index("Perfect Agen"):
				category.append("PA")
				make_time_helper.append("Agent")
		except:
			try:	
				if x.index("Secret"):
					category.append("SA")
					make_time_helper.append("Agent")
			except:
				try:
					if x.index("Special"):
						category.append("SA")
						make_time_helper.append("Agent")
				except:
					try:
						if x.index("00 Agen"):
							category.append("00A")
							make_time_helper.append("Agent")
					except:
						try:
							if x.index("Agent"):
								category.append("Agent")
								make_time_helper.append("Agent")
						except:
							try:
								if x.index("All 60"):
									category.append("All 60")
									make_time_helper.append("All 60")
							except:
								try:
									if x.index("100%"):	
										category.append("100%")
										make_time_helper.append("100%")
								except:
									pass

def make_time():

	for i in range(len(time_info)):
		x = ""
		c = ""

		if make_time_helper[i] == '100%':
			x = time_info[i]
			x = x.index("100%")
			x = x + 5
		elif make_time_helper[i] == 'Agent':
			x = time_info[i]
			x = x.index("Agent")
			x = x + 6
		elif make_time_helper[i] == 'All 60':
			x = time_info[i]
			x = x.index("All 60")
			x = x + 7

		c = time_info[i]
		c = c.index("by")
		c = c - 1

		f = time_info[i]
		f = f[x:c]

		if f == "N/A": # if player submits a time = to 20:00
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

		if(time_in_seconds[i] == "N/A"): # if player submits a time = to 20:00
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

	for i in range(len(time_info)):
		if "GoldenEye" in time_info[i]:
			game.append("ge")
		else:
			game.append("pd")

def make_filename():


	for i in range(len(time_info)):
		temp_category = category[i]

		if category[i] == '100%':
			temp_category = "100"

		new_filename = game[i] + "." + time_type[i].lower().replace(" ","") + "." + temp_category.replace(" ","") + "." + time_in_seconds[i] + "." + player[i] + ".mp4"
		filename.append(new_filename)


def make_folder():

	print("")
	print("Attempting to make directories... ")
	print("")

	for i in range(len(time_info)):
		
		try:
			#creates directory
			os.mkdir("E:\\the-elite-single-segment-videos\\" + player[i])
			print("Directory ", player[i], " created")
		except:
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

		my_cursor.execute("SELECT COUNT(*) FROM video_data WHERE rankings_url = (%s)", (rankings_url[updated_index],))
		num_Of_rankings_url_duplicates = my_cursor.fetchall()[0][0]

		my_cursor.execute("SELECT COUNT(*) FROM video_data WHERE youtube_url = (%s)", (youtube_url[updated_index],))
		num_Of_youtube_url_duplicates = my_cursor.fetchall()[0][0]

		my_cursor.execute("SELECT COUNT(*) FROM video_data WHERE rankings_id = (%s)", (rankings_id[updated_index],))
		num_Of_rankings_id_duplicates = my_cursor.fetchall()[0][0]


		if num_Of_rankings_id_duplicates != 0:
			rankings_url.pop(updated_index)
			youtube_url.pop(updated_index)
			time_info.pop(updated_index)		
			player.pop(updated_index)
			time_type.pop(updated_index)
			category.pop(updated_index)
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
		print("Time type: " + time_type[i])
		print("Player: " + player[i])
		print("Filename: " + filename[i])

		os.chdir("E:\\the-elite-single-segment-videos\\" + player[i] + "\\")

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

	addRow = "INSERT INTO video_data (game, time_type, category, time_in_seconds, regular_time, player, extension, youtube_url, published_date, rankings_url, filename, dead_youtube_url, rankings_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

	for i in range(len(time_info)):
		record = (game[i], time_type[i], category[i], str(int(time_in_seconds[i])), regular_time[i], player[i], "mp4", youtube_url[i], date_achieved[i], rankings_url[i], filename[i], dead_url[i], rankings_id[i])
		my_cursor.execute(addRow, record)
		mydb.commit() #save

	print("")
	print("Finished. Added info to database")


def main():

	refresh.delete_SingleSegment_Table()
	for counter in range(600,700):
		print("")
		get_yt_url(counter)
		get_time_info()
		for i in time_info:
			print(i)
		get_rankings_url_id()
		make_player_name()
		make_category()
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
		youtube_url.clear()		
		time_info.clear()		
		player.clear()
		category.clear()
		time_in_seconds.clear()
		game.clear()
		filename.clear()
		regular_time.clear()
		date_achieved.clear()
		dead_url.clear()
		rankings_id.clear()
		time_type.clear()
		make_time_helper.clear()

		
		print("")
		
main()