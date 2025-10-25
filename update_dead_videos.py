import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from yt_dlp import YoutubeDL
import config

class YTDLPLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        print("Warning:", msg)

    def error(self, msg):
        print("Error:", msg)

def is_youtube_alive(url: str) -> bool:
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'logger': YTDLPLogger(),
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=False)
        return True
    except Exception:
        return False

def get_already_checked(log_path="checked_videos.log"):
    if not os.path.exists(log_path):
        return set()
    with open(log_path, "r") as f:
        return set(line.strip().split(",")[0] for line in f if line.strip())

def append_to_log(url, status, log_path="checked_videos.log"):
    with open(log_path, "a") as f:
        f.write(f"{url},{status}\n")

def update_database(url, alive):
    if alive:
        config.my_cursor.execute(
            "UPDATE `the-elite-videos` SET dead_youtube_url = '0' WHERE youtube_url = %s",
            (url,)
        )
        print(url + " is alive.")
        append_to_log(url, "alive")
    else:
        config.my_cursor.execute(
            "UPDATE `the-elite-videos` SET dead_youtube_url = '1' WHERE youtube_url = %s",
            (url,)
        )
        print(url + " is dead.")
        append_to_log(url, "dead")
    config.cursor.commit()

def main():
    checked = get_already_checked()
    print(f"Skipping {len(checked)} already checked URLs.")

    config.my_cursor.execute("SELECT * FROM `the-elite-videos`;")
    rows = config.my_cursor.fetchall()
    
    urls_to_check = [row[7] for row in rows if row[7] not in checked]
    
    with ThreadPoolExecutor(max_workers=100) as executor:  # adjust number of threads
        future_to_url = {executor.submit(is_youtube_alive, url): url for url in urls_to_check}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            alive = future.result()
            update_database(url, alive)

if __name__ == "__main__":
    main()
