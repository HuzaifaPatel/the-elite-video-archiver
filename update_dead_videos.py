import config
from yt_dlp import YoutubeDL



def is_youtube_alive(url: str) -> bool:
	ydl_opts = {
		'quiet': True,
		'skip_download': True,
		'nocheckcertificate': True,
	}
	try:
		with YoutubeDL(ydl_opts) as ydl:
			ydl.extract_info(url, download=False)
		return True  # video exists
	except Exception as e:
		# Video is dead, private, or unavailable
		return False


# Use the MySQL cursor from config.py
config.my_cursor.execute("SELECT * FROM `the-elite-videos`;")
rows = config.my_cursor.fetchall()
for row in rows:
	if is_youtube_alive(row[7]):
		config.my_cursor.execute("UPDATE `the-elite-videos` SET dead_youtube_url = '0' WHERE youtube_url = %s", (row[7],))
		config.cursor.commit()
		print(row[7] + " is alive.")
	else:
		config.my_cursor.execute("UPDATE `the-elite-videos` SET dead_youtube_url = '1' WHERE youtube_url = %s", (row[7],))
		config.cursor.commit()
		print(row[7] + " is dead.")