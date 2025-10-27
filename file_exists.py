import config
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed

BUCKET = config.DO_SPACES_BUCKET
S3 = config.s3_client
DB = config.my_cursor

# --- Fetch all rows ---
DB.execute("SELECT * FROM `the-elite-videos`")
rows = DB.fetchall()

def check_file(row):
    """Check if a file exists in the S3 bucket using original column indexes."""
    folder = row[5]    # your folder column
    filename = row[10] # your filename column
    key = f"{folder}/{filename}"
    try:
        S3.head_object(Bucket=BUCKET, Key=key)
        return (filename, 1)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return (filename, 0)
        else:
            print(f"⚠️ Error checking {filename}: {e}")
            return None

results = []
updated = 0

# --- Use threads for faster S3 checking ---
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_file, row): row for row in rows}
    for future in as_completed(futures):
        res = future.result()
        if res:
            results.append(res)
            updated += 1
            filename, exists = res
            print(f"{filename}: {'✅ exists' if exists else '❌ missing'}")

# --- Batch update the database ---
update_query = "UPDATE `the-elite-videos` SET file_exists = %s WHERE filename = %s"
for filename, exists in results:
    DB.execute(update_query, (exists, filename))

config.cursor.commit()

print(f"\n✅ Done! Updated {updated} entries.")
