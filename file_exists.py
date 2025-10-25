"""
This script goes through the DB and for each entry, it checks if the filename is in the bucket.
If it is not, then file_exists is updated to 0. Otherwise, it is updated to 1.
"""

import config
from botocore.exceptions import ClientError
BUCKET = config.DO_SPACES_BUCKET

# --- Fetch all filenames ---
config.my_cursor.execute("SELECT * FROM `the-elite-videos`")
rows = config.my_cursor.fetchall()

updated = 0
for row in rows:
	try:
		config.s3_client.head_object(Bucket=BUCKET, Key=row[5] + "/" + row[10])
		file_exists = 1
	except ClientError as e:
		if e.response["Error"]["Code"] == "404":
			file_exists = 0
		else:
			print(f"⚠️ Error checking {row[10]}: {e}")
			continue

	config.my_cursor.execute(
		"UPDATE `the-elite-videos` SET file_exists = %s WHERE filename = %s", (file_exists, row[10])
	)
	config.cursor.commit()
	updated += 1
	print(f"{row[10]}: {'✅ exists' if file_exists else '❌ missing'}")

print(f"\n✅ Done! Updated {updated} entries.")