import boto3
import config
from collections import defaultdict

def clean_duplicate_videos_optimized():
    """
    Efficiently finds duplicate videos in DO Spaces (same base filename, different extensions).
    Deletes files whose extension is not recorded in the database.
    """
    # Step 1: List all objects and group by base name
    paginator = config.s3_client.get_paginator('list_objects_v2')
    files_by_base = defaultdict(list)  # { "player/video" : ["mp4", "webm"] }

    for page in paginator.paginate(Bucket=config.DO_SPACES_BUCKET):
        for obj in page.get('Contents', []):
            key = obj['Key']  # e.g., 'player/video.mp4'
            if '/' not in key or '.' not in key:
                continue  # skip invalid keys
            base_name = '.'.join(key.split('.')[:-1])  # everything except extension
            ext = key.split('.')[-1]
            files_by_base[base_name].append((key, ext))

    # Step 2: Compare with database and delete extras
    deleted_files = 0
    duplicates_found = 0

    for base_name, files in files_by_base.items():
        if len(files) <= 1:
            continue  # not a duplicate

        duplicates_found += 1
        player = base_name.split('/')[0]

        # Get the recorded extension from the DB
        query = "SELECT extension FROM `the-elite-videos` WHERE player=%s AND filename LIKE %s"
        config.my_cursor.execute(query, (player, base_name.split('/', 1)[1] + '%'))
        result = config.my_cursor.fetchone()

        if result:
            db_extension = result[0]
            for key, ext in files:
                if ext != db_extension:
                    # Delete extra extension
                    try:
                        config.s3_client.delete_object(Bucket=config.DO_SPACES_BUCKET, Key=key)
                        print(f"Deleted duplicate: {key} (DB has .{db_extension})")
                        deleted_files += 1
                    except Exception as e:
                        print(f"Failed to delete {key}: {e}")
        else:
            print(f"No DB record found for base {base_name}, skipping all duplicates.")

    print(f"Found {duplicates_found} duplicate sets. Deleted {deleted_files} files.")

if __name__ == "__main__":
    clean_duplicate_videos_optimized()