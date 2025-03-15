import mysql.connector
from mysql.connector import Error
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import time
import os

# Replace with your DigitalOcean Spaces credentials
DO_SPACES_KEY = "H3NOCAUHMQGTA2ALEU3E"
DO_SPACES_SECRET = "dMmiEqbRtUfpadtS4bLZgfagYSGq6WZYRopA1EPvr2I"
DO_SPACES_REGION = "nyc3"
DO_SPACES_BUCKET = "the-elite-videos"
DO_SPACES_ENDPOINT = f"https://{DO_SPACES_REGION}.digitaloceanspaces.com"

# Initialize DigitalOcean Spaces Client
s3_client = boto3.client(
    "s3",
    region_name=DO_SPACES_REGION,
    endpoint_url=DO_SPACES_ENDPOINT,
    aws_access_key_id=DO_SPACES_KEY,
    aws_secret_access_key=DO_SPACES_SECRET,
    config=Config(signature_version="s3v4",
        connect_timeout=60,    # Increase if needed
        read_timeout=120,      # Increase if needed
        retries={
            'max_attempts': 10,
            'mode': 'standard'
        }
    )
)

def delete_object_if_exists(bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        # If a 404 status code, the object doesn’t exist
        if e.response['Error']['Code'] == "404":
            print(f"Object '{key}' does not exist, so it can't be deleted.")
        else:
            # Some other error occurred
            print(f"Error checking object: {e}")
        return

    # 2. Delete the object
    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
        print(f"Deleted object '{key}' from bucket '{bucket}'.")
    except ClientError as e:
        print(f"Error deleting object '{key}': {e}")


def go_through_all_objects():
    keys = []
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=DO_SPACES_BUCKET):
        for obj in page.get('Contents', []):
            keys.append(obj['Key'])
    return keys

def rename_object_if_exists(bucket, old_key, new_key):
    """
    Check if `old_key` exists in `bucket`. If it does:
      1) Copy it to `new_key`.
      2) Delete the original `old_key`.
    """
    # 1. Check if the old_key exists:
    try:
        s3_client.head_object(Bucket=bucket, Key=old_key)
    except ClientError as e:
        # If a 404 status code, the object doesn’t exist
        if e.response['Error']['Code'] == "404":
            print(f"Object '{old_key}' does not exist, so it can't be renamed.")
        else:
            # Some other error occurred
            print(f"Error checking object: {e}")
        return

    # 2. Copy the object to new_key
    try:
        copy_source = {
            'Bucket': bucket,
            'Key': old_key
        }
        s3_client.copy_object(
            Bucket=bucket,
            CopySource=copy_source,
            Key=new_key
        )
        print(f"Copied '{old_key}' to '{new_key}'.")
    except ClientError as e:
        print(f"Error copying object: {e}")
        return

    # 3. Delete the old object
    try:
        s3_client.delete_object(Bucket=bucket, Key=old_key)
        print(f"Deleted original object '{old_key}'.")
    except ClientError as e:
        print(f"Error deleting old object: {e}")

def connect_to_mysql(host, database, user, password, port=3306):
    """
    Connects to a remote MySQL server and returns the connection object.
    """
    try:
        # Initialize the connection
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        if connection.is_connected():
            print("Connected to MySQL Server")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def connect_to_db():
    # Replace with your actual MySQL server details
    host = "huzip.net"
    user = "huzi"
    password = "theelitehuzi007"
    database = "the-elite-videos"
    port = 3306  # Default MySQL port

    return connect_to_mysql(host, database, user, password, port)

def download_object_same_structure(bucket, key, s3_client):
    """
    Downloads an object from a DigitalOcean Spaces bucket,
    placing it under a local base folder named after the bucket.

    For example, if the bucket is "the-elite-videos" and `key` is "folder/subfolder/file.mp4",
    the file will be saved locally as:
        "./the-elite-videos/folder/subfolder/file.mp4"

    :param bucket:      The name of the Spaces bucket.
    :param key:         The object key (path/name) in the bucket.
    :param s3_client:   A configured boto3 S3 client for DigitalOcean Spaces.
    """

    # Use the bucket name as the local base directory
    base_dir = bucket

    # Combine the base directory with the object key
    local_path = os.path.join(base_dir, key)

    # Ensure that the local directories exist
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    # (1) Check if the object exists in the bucket
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            print(f"Object '{key}' does not exist in bucket '{bucket}'.")
        else:
            print(f"Error checking object: {e}")
        return  # Stop if the object doesn't exist or there's another error

    # (2) Download the object
    try:
        s3_client.download_file(bucket, key, local_path)
        print(f"Downloaded '{key}' from bucket '{bucket}' to '{local_path}'.")
    except ClientError as e:
        print(f"Error downloading object '{key}': {e}")

def change_file_name():
    connection = connect_to_db()
    
    if connection:
        try:
            # Create a new cursor
            cursor = connection.cursor()            
            cursor.execute("SELECT * FROM `video_data`")
            data = cursor.fetchall()
            
            for dat in data:
                new_filename = dat[10].split(".")
                new_filename.insert(len(new_filename)-1, dat[12])
                new_filename = '.'.join(str(part) for part in new_filename)
                # print(new_filename)
                rename_object_if_exists("the-elite-videos", dat[5] + "/" + dat[10], dat[5] + "/" + new_filename)
                time.sleep(0.1)
        except Error as e:
            print(f"Error during query execution: {e}")
        
        finally:
            # Close cursor and connection
            cursor.close()
            connection.close()


def find_duplicates():
    # Dictionary to store items by their key (the 6th element)
    items_by_key = {}
    
    # Get your list of objects
    lis = go_through_all_objects()

    # Organize items by key (only for those that split into 7 parts)
    for i in lis:
        key_lis = i.split(".")
        if len(key_lis) == 7:
            key = key_lis[5]
            # Append this item to the list for this key.
            items_by_key.setdefault(key, []).append(i)
    
    duplicates_count = 0
    # Iterate through our dictionary, and if a key has more than one item,
    # print all the items for that key.
    for key, items in items_by_key.items():
        if len(items) > 1:
            duplicates_count += len(items)
            for item in items:
                print(item)
    
    print("Total duplicate items (all instances):", duplicates_count)




def main():
    find_duplicates()


# Example call to main()
if __name__ == "__main__":
    main()