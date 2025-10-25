"""
If a player changes their name on the rankings, we need to change it in the bucket. This does it for us.
"""


import os

PATH = "/home/huzi/Downloads/Ryan_White"
NEW_NAME = "Ryan_W."
os.chdir(PATH)

def change_name():
	for file in os.listdir():
		old_filename = file 
		file = file.split(".")

		if file[5] == '':
			del file[5]
			file[4] = file[4] + "."

		file[4] = NEW_NAME
		file = ".".join(file)
		new_filename = file
		os.rename(old_filename, new_filename)

change_name()