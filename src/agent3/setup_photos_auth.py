import os
import json
import urllib.parse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import requests

# If modifying these scopes, delete the file photos_token.json.
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

def main():
    """Shows basic usage of the Photos v1 API.
    Prints the names and ids of the first 10 albums.
    """
    creds = None
    # The file photos_token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('photos_token.json'):
        creds = Credentials.from_authorized_user_file('photos_token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            # Check the parent directory as well
            secret_path = 'client_secret.json'
            if not os.path.exists(secret_path):
                secret_path = '../../client_secret.json'
                if not os.path.exists(secret_path):
                    print(f"❌ ERROR: client_secret.json not found in current directory or project root!")
                    print("Please download your OAuth 2.0 Client ID (Desktop App) from Google Cloud Console and save it as client_secret.json.")
                    return
            
            print("Initiating new OAuth flow. A browser window should open...")
            flow = InstalledAppFlow.from_client_secrets_file(
                secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('photos_token.json', 'w') as token:
            token.write(creds.to_json())
            print("✅ Saved new credentials to photos_token.json")

    print("\n✅ Successfully Authenticated!")
    
    # Use requests to hit the Photos Library API
    access_token = creds.token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    print("\nFetching your albums to find 'Leo-source'...")
    url = "https://photoslibrary.googleapis.com/v1/albums"
    params = {'pageSize': 50}
    
    leo_album_id = None
    
    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"❌ Error fetching albums: {response.status_code}")
            print(response.text)
            break
            
        data = response.json()
        albums = data.get('albums', [])
        
        for album in albums:
            title = album.get('title', '')
            album_id = album.get('id')
            item_count = album.get('mediaItemsCount', '0')
            print(f"- Found Album: '{title}' ({item_count} items)")
            
            if title.lower() == 'leo-source':
                leo_album_id = album_id
                
        next_page_token = data.get('nextPageToken')
        if not next_page_token or leo_album_id:
            break
        params['pageToken'] = next_page_token
        
    if leo_album_id:
        print("\n" + "="*50)
        print(f"🎉 FOUND TARGET ALBUM: Leo-source")
        print(f"ALBUM_ID = {leo_album_id}")
        print("="*50 + "\n")
        print("Add this ALBUM_ID to your .env file or configuration for Agent #3 to use.")
    else:
        print("\n❌ Could not find an album named 'Leo-source'. Did you create it yet?")

if __name__ == '__main__':
    main()
