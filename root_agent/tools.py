# tools.py - Email utilities following Calendar integration pattern
"""
Utility functions for Gmail integration.
"""
import json
import os
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Define scopes needed for Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Path for token storage
TOKEN_PATH = Path(os.path.expanduser("~/.credentials/gmail_token.json"))
CREDENTIALS_PATH = Path("credentials.json")

def get_gmail_service():
    """
    Authenticate and create a Gmail service object.
    
    Returns:
        A Gmail service object or None if authentication fails
    """
    creds = None
    
    # Check if token exists and is valid
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_info(
            json.loads(TOKEN_PATH.read_text()), SCOPES
        )
    
    # If credentials don't exist or are invalid, refresh or get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # If credentials.json doesn't exist, we can't proceed with OAuth flow
            if not CREDENTIALS_PATH.exists():
                print(
                    f"Error: {CREDENTIALS_PATH} not found. Please follow setup instructions."
                )
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())
    
    # Create and return the Gmail service
    return build("gmail", "v1", credentials=creds)

def extract_message_body(payload):
    """
    Extract the body from email payload.
    
    Args:
        payload (dict): The email payload from Gmail API
        
    Returns:
        str: The email body content
    """
    body = ""
    
    try:
        if "parts" in payload:
            # Multi-part message
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data")
                    if data:
                        body += base64.urlsafe_b64decode(data + "===").decode("utf-8", errors='ignore')
                elif part["mimeType"] == "text/html" and not body:
                    # If no plain text found, use HTML
                    data = part["body"].get("data")
                    if data:
                        body = base64.urlsafe_b64decode(data + "===").decode("utf-8", errors='ignore')
        else:
            # Single part message
            if payload["mimeType"] == "text/plain":
                data = payload["body"].get("data")
                if data:
                    body = base64.urlsafe_b64decode(data + "===").decode("utf-8", errors='ignore')
            elif payload["mimeType"] == "text/html":
                data = payload["body"].get("data")
                if data:
                    body = base64.urlsafe_b64decode(data + "===").decode("utf-8", errors='ignore')
    except Exception as e:
        body = f"Error extracting email body: {e}"
    
    return body

def format_email_time(date_str):
    """
    Format an email date string into a human-readable string.
    
    Args:
        date_str (str): The date string from email headers
        
    Returns:
        str: A human-readable date string
    """
    if not date_str:
        return "Unknown date"
    
    try:
        # Try to parse the email date format
        # Email dates are typically in RFC 2822 format
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        return date_str

def parse_email_search_query(search_terms):
    """
    Parse search terms into Gmail search query format.
    
    Args:
        search_terms (str): Natural language search terms
        
    Returns:
        str: Gmail search query
    """
    # Simple parsing - can be enhanced for more complex queries
    search_terms = search_terms.lower().strip()
    
    # Common search patterns
    if "unread" in search_terms:
        return "is:unread"
    elif "from:" in search_terms:
        return search_terms
    elif "subject:" in search_terms:
        return search_terms
    elif "attachment" in search_terms:
        return "has:attachment"
    else:
        return search_terms

def get_current_time() -> dict:
    """
    Get the current time and date for email operations
    """
    now = datetime.now()
    # Format date as MM-DD-YYYY
    formatted_date = now.strftime("%m-%d-%Y")
    return {
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "formatted_date": formatted_date,
    }


def get_recent_emails(max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Get a list of recent emails from Gmail.
    
    Args:
        max_results: Maximum number of emails to retrieve (default: 10)
    
    Returns:
        List of email metadata including sender, subject, date, and snippet
    """
    service = get_gmail_service()
    if not service:
        return [{"error": "Failed to authenticate with Gmail service"}]
    
    try:
        results = service.users().messages().list(
            userId="me", 
            maxResults=max_results
        ).execute()
        
        messages = results.get("messages", [])
        if not messages:
            return [{"message": "No emails found"}]
            
        email_list = []
        
        for message in messages:
            try:
                # Get basic message info
                msg = service.users().messages().get(
                    userId="me", 
                    id=message["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"]
                ).execute()
                
                # Extract headers
                headers = msg["payload"].get("headers", [])
                email_info = {"id": message["id"]}
                
                for header in headers:
                    name = header["name"]
                    if name in ["From", "To", "Subject", "Date"]:
                        email_info[name.lower()] = header["value"]
                
                # Format the date
                if "date" in email_info:
                    email_info["formatted_date"] = format_email_time(email_info["date"])
                
                # Add snippet and thread info
                email_info["snippet"] = msg.get("snippet", "")
                email_info["thread_id"] = msg.get("threadId", "")
                
                email_list.append(email_info)
                
            except Exception as e:
                email_list.append({"id": message["id"], "error": f"Failed to retrieve email: {e}"})
        
        return email_list
    
    except HttpError as error:
        return [{"error": f"Gmail API error: {error}"}]
    except Exception as e:
        return [{"error": f"Unexpected error: {e}"}]


def read_email_content(message_id: str) -> Dict[str, Any]:
    """
    Read the full content of a specific email by its ID.
    
    Args:
        message_id: The ID of the message to read
    
    Returns:
        Dictionary containing full email content and metadata
    """
    service = get_gmail_service()
    if not service:
        return {"error": "Failed to authenticate with Gmail service"}
    
    try:
        message = service.users().messages().get(
            userId="me", 
            id=message_id,
            format="full"
        ).execute()
        
        # Extract headers
        headers = message["payload"].get("headers", [])
        email_data = {"id": message_id}
        
        for header in headers:
            name = header["name"]
            if name in ["From", "To", "Subject", "Date", "Cc", "Bcc"]:
                email_data[name.lower()] = header["value"]
        
        # Format the date
        if "date" in email_data:
            email_data["formatted_date"] = format_email_time(email_data["date"])
        
        # Extract body
        email_data["body"] = extract_message_body(message["payload"])
        email_data["snippet"] = message.get("snippet", "")
        email_data["thread_id"] = message.get("threadId", "")
        email_data["label_ids"] = message.get("labelIds", [])
        
        return email_data
    
    except HttpError as error:
        return {"error": f"Gmail API error: {error}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def search_emails(query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """
    Search emails using Gmail search syntax.
    
    Args:
        query: Gmail search query (e.g., "is:unread", "from:example@gmail.com", "subject:meeting")
        max_results: Maximum number of results to return
    
    Returns:
        List of matching emails with metadata
    """
    service = get_gmail_service()
    if not service:
        return [{"error": "Failed to authenticate with Gmail service"}]
    
    # Parse and optimize the search query
    parsed_query = parse_email_search_query(query)
    
    try:
        results = service.users().messages().list(
            userId="me", 
            q=parsed_query, 
            maxResults=max_results
        ).execute()
        
        messages = results.get("messages", [])
        if not messages:
            return [{"message": f"No emails found for query: {query}"}]
            
        email_list = []
        
        for message in messages:
            try:
                # Get basic message info
                msg = service.users().messages().get(
                    userId="me", 
                    id=message["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"]
                ).execute()
                
                # Extract headers
                headers = msg["payload"].get("headers", [])
                email_info = {"id": message["id"]}
                
                for header in headers:
                    name = header["name"]
                    if name in ["From", "To", "Subject", "Date"]:
                        email_info[name.lower()] = header["value"]
                
                # Format the date
                if "date" in email_info:
                    email_info["formatted_date"] = format_email_time(email_info["date"])
                
                # Add snippet and thread info
                email_info["snippet"] = msg.get("snippet", "")
                email_info["thread_id"] = msg.get("threadId", "")
                
                email_list.append(email_info)
                
            except Exception as e:
                email_list.append({"id": message["id"], "error": f"Failed to retrieve email: {e}"})
        
        return email_list
    
    except HttpError as error:
        return [{"error": f"Gmail API error: {error}"}]
    except Exception as e:
        return [{"error": f"Unexpected error: {e}"}]


def get_unread_emails(max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Get all unread emails from Gmail.
    
    Args:
        max_results: Maximum number of unread emails to retrieve
    
    Returns:
        List of unread emails with metadata
    """
    return search_emails("is:unread", max_results)


def get_emails_from_sender(sender_email: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Get emails from a specific sender.
    
    Args:
        sender_email: Email address of the sender
        max_results: Maximum number of emails to retrieve
    
    Returns:
        List of emails from the specified sender
    """
    query = f"from:{sender_email}"
    return search_emails(query, max_results)


def get_emails_with_subject(subject_keywords: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Get emails containing specific keywords in the subject line.
    
    Args:
        subject_keywords: Keywords to search for in email subjects
        max_results: Maximum number of emails to retrieve
    
    Returns:
        List of emails matching the subject criteria
    """
    query = f"subject:{subject_keywords}"
    return search_emails(query, max_results)


def get_emails_by_date_range(start_date: str, end_date: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
    """
    Get emails within a specific date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        max_results: Maximum number of emails to retrieve
    
    Returns:
        List of emails within the date range
    """
    if end_date:
        query = f"after:{start_date} before:{end_date}"
    else:
        query = f"after:{start_date}"
    
    return search_emails(query, max_results)


def get_gmail_labels() -> List[Dict[str, str]]:
    """
    Get all Gmail labels/folders.
    
    Returns:
        List of Gmail labels with their IDs and names
    """
    service = get_gmail_service()
    if not service:
        return [{"error": "Failed to authenticate with Gmail service"}]
    
    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        return [{"id": label["id"], "name": label["name"]} for label in labels]
    except HttpError as error:
        return [{"error": f"Gmail API error: {error}"}]
    except Exception as e:
        return [{"error": f"Unexpected error: {e}"}]


def get_email_statistics() -> Dict[str, Any]:
    """
    Get email statistics and insights.
    
    Returns:
        Dictionary containing email statistics
    """
    service = get_gmail_service()
    if not service:
        return {"error": "Failed to authenticate with Gmail service"}
    
    try:
        # Get basic stats
        unread_count = len(search_emails("is:unread", 1000))
        total_labels = len(get_gmail_labels())
        recent_emails = len(get_recent_emails(100))
        
        # Get current time info
        time_info = get_current_time()
        
        return {
            "unread_count": unread_count,
            "total_labels": total_labels,
            "recent_emails_count": recent_emails,
            "last_checked": time_info["current_time"],
            "date": time_info["formatted_date"]
        }
    
    except Exception as e:
        return {"error": f"Failed to get email statistics: {e}"}

 
def check_gmail_setup() -> Dict[str, Any]:
    """
    Check Gmail API setup and provide setup instructions if needed.
    
    Returns:
        Dictionary with setup status and instructions
    """
    try:
        # Check if credentials file exists
        if not CREDENTIALS_PATH.exists():
            return {
                "status": "error",
                "message": "Gmail API credentials not found",
                "credentials_path": str(CREDENTIALS_PATH),
                "instructions": [
                    "1. Go to Google Cloud Console (https://console.cloud.google.com/)",
                    "2. Create a new project or select existing project",
                    "3. Enable Gmail API (APIs & Services > Library > Gmail API)",
                    "4. Create credentials (APIs & Services > Credentials > Create Credentials > OAuth 2.0 Client IDs)",
                    "5. Choose 'Desktop Application' as application type",
                    "6. Download the JSON file and save as 'credentials.json' in your project directory"
                ]
            }
        
        # Try to get Gmail service
        service = get_gmail_service()
        if not service:
            return {
                "status": "error",
                "message": "Failed to create Gmail service",
                "instructions": [
                    "Check that your credentials.json file is valid",
                    "Ensure Gmail API is enabled in your Google Cloud project",
                    "Verify that you're using Desktop Application credentials"
                ]
            }
        
        # Test API call
        try:
            service.users().getProfile(userId="me").execute()
            time_info = get_current_time()
            
            return {
                "status": "success",
                "message": "Gmail API is properly configured and authenticated",
                "credentials_path": str(CREDENTIALS_PATH),
                "token_path": str(TOKEN_PATH),
                "last_checked": time_info["current_time"]
            }
            
        except Exception as e:
            return {
                "status": "partial",
                "message": "Gmail service created but API call failed",
                "error": str(e),
                "instructions": [
                    "Gmail service exists but API calls are failing",
                    "Check your internet connection",
                    "Verify that Gmail API is enabled",
                    "Try deleting the token file to force re-authentication"
                ]
            }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Setup check failed: {e}",
            "instructions": [
                "An unexpected error occurred during setup check",
                "Please check your Google Cloud Console configuration",
                "Ensure Gmail API is enabled and credentials are properly configured"
            ]
        }

# Utility functions for formatting output
def format_email_summary(emails: List[Dict[str, Any]]) -> str:
    """
    Format a list of emails into a readable summary.
    
    Args:
        emails: List of email dictionaries
        
    Returns:
        str: Formatted email summary
    """
    if not emails:
        return "No emails found."
    
    if isinstance(emails[0], dict) and "error" in emails[0]:
        return f"Error: {emails[0]['error']}"
    
    summary = f"Found {len(emails)} emails:\n\n"
    
    for i, email in enumerate(emails, 1):
        if "error" in email:
            summary += f"{i}. Error: {email['error']}\n\n"
            continue
            
        sender = email.get('from', 'Unknown sender')
        subject = email.get('subject', 'No subject')
        formatted_date = email.get('formatted_date', email.get('date', 'Unknown date'))
        snippet = email.get('snippet', '')[:100] + "..." if len(email.get('snippet', '')) > 100 else email.get('snippet', '')
        
        summary += f"{i}. From: {sender}\n"
        summary += f"   Subject: {subject}\n"  
        summary += f"   Date: {formatted_date}\n"
        summary += f"   Preview: {snippet}\n\n"
    
    return summary

def format_email_content(email_data: Dict[str, Any]) -> str:
    """
    Format email content for display.
    
    Args:
        email_data: Email data dictionary
        
    Returns:
        str: Formatted email content
    """
    if "error" in email_data:
        return f"Error reading email: {email_data['error']}"
    
    content = f"EMAIL DETAILS:\n"
    content += f"From: {email_data.get('from', 'Unknown')}\n"
    content += f"To: {email_data.get('to', 'Unknown')}\n"
    content += f"Subject: {email_data.get('subject', 'No Subject')}\n"
    content += f"Date: {email_data.get('formatted_date', email_data.get('date', 'Unknown'))}\n"
    
    if email_data.get('cc'):
        content += f"CC: {email_data.get('cc')}\n"
    
    content += f"\nContent:\n{email_data.get('body', 'No content available')}\n"
    
    return content