"""
This script takes a filename ge.archives.00A.0054.June_X..174044.webm and turns it into June X. - Archives 00A 0:54
"""
import os

FILE_LOCATION = "/home/huzi/Downloads/June_X."

def get_files():
	os.chdir(FILE_LOCATION)

	for file in os.listdir():
		change_name(file)

def change_username(new_filename, old_username, new_username):
	return new_filename.replace(old_username, new_username)

def change_name(file):
	stripped_file = file.split(".")

	if stripped_file[5] == '':
		del stripped_file[5]
		stripped_file[4] = stripped_file[4] + "."
	
	del stripped_file[5]
	extension = stripped_file[-1]
	del stripped_file[5]
	del stripped_file[0]
	stripped_file[0] = stripped_file[0].capitalize()

	seconds_total = int(stripped_file[2])
	minutes = seconds_total // 60      # integer division gives minutes
	seconds = seconds_total % 60       # remainder gives remaining seconds

	formatted_time = f"{minutes}:{seconds:02}"  # :02 ensures 2 digits for seconds
	stripped_file[2] = formatted_time

	stripped_file[0], stripped_file[3] = stripped_file[3], stripped_file[0]
	stripped_file.insert(1, "-")
	stripped_file[2], stripped_file[4] = stripped_file[4], stripped_file[2]
	stripped_file[3], stripped_file[4] = stripped_file[4], stripped_file[3]
	new_filename = ' '.join(stripped_file) + "." + extension
	new_filename = change_username(new_filename, "June_X.", "Celeste I.")
	change_file_name(file, new_filename)

def change_file_name(file, new_filename):
	os.rename(file, new_filename)


if __name__ == "__main__":
	get_files()