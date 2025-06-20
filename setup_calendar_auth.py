#!/usr/bin/env python3
"""
Gmail Authentication Setup Script

This script helps you set up OAuth 2.0 credentials for Gmail integration.
Follow the instructions in the console.
"""

import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define scopes needed for Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Path for token storage
TOKEN_PATH = Path(os.path.expanduser("~/.credentials/gmail_token.json"))
CREDENTIALS_PATH = Path("credentials.json")


def setup_oauth():
    """Set up OAuth 2.0 for Gmail"""
    print("\n=== Gmail OAuth Setup ===\n")

    if not CREDENTIALS_PATH.exists():
        print(f"Error: {CREDENTIALS_PATH} not found!")
        print("\nTo set up Gmail integration:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select an existing one")
        print("3. Enable the Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop application)")
        print(
            "5. Download the credentials and save them as 'credentials.json' in this directory"
        )
        print("\nIMPORTANT: Make sure to select 'Desktop Application' type, NOT 'Web Application'!")
        print("\nThen run this script again.")
        return False

    print(f"Found credentials.json. Setting up OAuth flow...")

    try:
        # Run the OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())

        print(f"\nSuccessfully saved credentials to {TOKEN_PATH}")

        # Test the API connection
        print("\nTesting connection to Gmail API...")
        service = build("gmail", "v1", credentials=creds)
        
        # Get user profile to test connection
        profile = service.users().getProfile(userId="me").execute()
        email_address = profile.get("emailAddress", "Unknown")
        total_messages = profile.get("messagesTotal", 0)
        
        print(f"\nSuccess! Connected to Gmail API:")
        print(f"- Email: {email_address}")
        print(f"- Total messages: {total_messages}")
        
        # Get labels to further test functionality
        print("\nTesting Gmail labels access...")
        labels_result = service.users().labels().list(userId="me").execute()
        labels = labels_result.get("labels", [])
        
        if labels:
            print(f"Found {len(labels)} labels:")
            for label in labels[:5]:  # Show first 5 labels
                print(f"- {label['name']} (ID: {label['id']})")
            if len(labels) > 5:
                print(f"... and {len(labels) - 5} more labels")
        
        # Test getting recent emails
        print("\nTesting email retrieval...")
        messages_result = service.users().messages().list(
            userId="me", 
            maxResults=3
        ).execute()
        messages = messages_result.get("messages", [])
        
        if messages:
            print(f"Successfully retrieved {len(messages)} recent emails")
            for i, message in enumerate(messages, 1):
                # Get email details
                msg = service.users().messages().get(
                    userId="me", 
                    id=message["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()
                
                headers = msg["payload"].get("headers", [])
                email_info = {}
                
                for header in headers:
                    name = header["name"]
                    if name in ["From", "Subject", "Date"]:
                        email_info[name.lower()] = header["value"]
                
                print(f"  {i}. From: {email_info.get('from', 'Unknown')[:50]}...")
                print(f"     Subject: {email_info.get('subject', 'No Subject')[:50]}...")
        else:
            print("No recent emails found (this is unusual but not necessarily an error)")

        print(
            "\nOAuth setup complete! You can now use the Gmail integration."
        )
        print("\nNext steps:")
        print("- Your Gmail agent is ready to use")
        print("- The token will be automatically refreshed when needed")
        print("- You can now run your email agent tools")
        
        return True

    except Exception as e:
        print(f"\nError during setup: {str(e)}")
        
        # Provide specific error guidance
        error_str = str(e).lower()
        if "client secrets must be for a web or installed app" in error_str:
            print("\nTROUBLESHOOTING:")
            print("This error means your credentials.json is for a 'Web Application'")
            print("You need 'Desktop Application' credentials instead.")
            print("\nTo fix this:")
            print("1. Go to Google Cloud Console > APIs & Services > Credentials")
            print("2. Create new OAuth 2.0 Client ID")
            print("3. Select 'Desktop Application' (NOT Web Application)")
            print("4. Download the new credentials.json")
            print("5. Replace your current credentials.json file")
            print("6. Run this setup script again")
        
        elif "gmail api" in error_str and "not enabled" in error_str:
            print("\nTROUBLESHOOTING:")
            print("Gmail API is not enabled for your project.")
            print("\nTo fix this:")
            print("1. Go to Google Cloud Console > APIs & Services > Library")
            print("2. Search for 'Gmail API'")
            print("3. Click on Gmail API and press 'Enable'")
            print("4. Run this setup script again")
        
        elif "access" in error_str or "permission" in error_str:
            print("\nTROUBLESHOOTING:")
            print("Permission or access denied error.")
            print("\nTo fix this:")
            print("1. Make sure you're logged into the correct Google account")
            print("2. Check that your OAuth consent screen is properly configured")
            print("3. Add your email to 'Test users' in the OAuth consent screen")
            print("4. Try running the setup again")
        
        return False


def check_existing_setup():
    """Check if Gmail setup already exists and is working"""
    print("\n=== Checking Existing Gmail Setup ===\n")
    
    if TOKEN_PATH.exists():
        print(f"Found existing token at {TOKEN_PATH}")
        try:
            from google.oauth2.credentials import Credentials
            import json
            
            # Load existing credentials
            creds = Credentials.from_authorized_user_info(
                json.loads(TOKEN_PATH.read_text()), SCOPES
            )
            
            if creds and creds.valid:
                print("Existing token is valid!")
                
                # Test the connection
                service = build("gmail", "v1", credentials=creds)
                profile = service.users().getProfile(userId="me").execute()
                email_address = profile.get("emailAddress", "Unknown")
                
                print(f"Successfully connected to Gmail: {email_address}")
                print("Your Gmail integration is already set up and working!")
                return True
            else:
                print("Existing token is invalid or expired.")
                if creds and creds.expired and creds.refresh_token:
                    print("Attempting to refresh token...")
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                    TOKEN_PATH.write_text(creds.to_json())
                    print("Token refreshed successfully!")
                    return True
                else:
                    print("Token cannot be refreshed. Need to re-authenticate.")
                    return False
                    
        except Exception as e:
            print(f"Error checking existing token: {e}")
            return False
    else:
        print("No existing Gmail token found.")
        return False


def main():
    """Main setup function"""
    print("Gmail API Setup and Authentication")
    print("=" * 40)
    
    # First check if setup already exists
    if check_existing_setup():
        print("\n✅ Gmail integration is already working!")
        
        response = input("\nWould you like to re-authenticate anyway? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Setup complete. You can use your Gmail agent now.")
            return
        else:
            print("Proceeding with re-authentication...")
    
    # Run the OAuth setup
    success = setup_oauth()
    
    if success:
        print("\n🎉 Gmail integration setup successful!")
        print("\nYou can now:")
        print("- Use the get_recent_emails() function")
        print("- Search emails with search_emails()")
        print("- Read email content with read_email_content()")
        print("- And all other Gmail agent tools!")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")
        print("For additional help, visit: https://developers.google.com/gmail/api/quickstart/python")


if __name__ == "__main__":
    main()