import os
from google.auth import default
from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials
from googleapiclient.discovery import build

def main():
    # 1. The target folder ID and Service Account
    FOLDER_ID = "YOUR_DRIVE_FOLDER_ID"
    SERVICE_ACCOUNT_EMAIL = "your-service-account@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com"
    
    print(f"🔄 Authenticating as user and impersonating: {SERVICE_ACCOUNT_EMAIL}...")
    
    # 2. Get the base Application Default Credentials (ADC)
    # This uses your current gcloud login (admin@yaninaso.altostrat.com)
    base_credentials, project = default()
    
    # 3. Create impersonated credentials for the Service Account
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = ImpersonatedCredentials(
        source_credentials=base_credentials,
        target_principal=SERVICE_ACCOUNT_EMAIL,
        target_scopes=scopes,
    )
    
    # 4. Build the Drive API service
    service = build('drive', 'v3', credentials=creds)
    
    print(f"\n📂 Fetching files from Google Drive Folder ID: {FOLDER_ID}")
    
    # 5. Query for files inside the folder
    query = f"'{FOLDER_ID}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        pageSize=10,
        fields="nextPageToken, files(id, name, mimeType)"
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        print("⚠️ No files found in the folder. (Are you sure you shared it with the service account?)")
    else:
        print("\n✅ Successfully connected! Found the following files:")
        for item in items:
            print(f" - {item['name']} (ID: {item['id']})")
            
if __name__ == '__main__':
    main()
