
# agent.py - Email agent following calendar pattern
from google.adk.agents import Agent
from .tools import (
    get_recent_emails, 
    read_email_content, 
    search_emails, 
    get_unread_emails,
    get_emails_from_sender,
    get_emails_with_subject,
    get_emails_by_date_range,
    get_gmail_labels,
    get_email_statistics,
    check_gmail_setup
)
from .prompts import EMAIL_AGENT_INSTRUCTIONS, EMAIL_AGENT_DESCRIPTION

# Main email management agent
root_agent = Agent(
    name="root_agent",
    model="gemini-2.0-flash",
    description=EMAIL_AGENT_DESCRIPTION,
    instruction=EMAIL_AGENT_INSTRUCTIONS,
    tools=[
        get_recent_emails,
        read_email_content,
        search_emails,
        get_unread_emails,
        get_emails_from_sender,
        get_emails_with_subject,
        get_emails_by_date_range,
        get_gmail_labels,
        get_email_statistics,
        check_gmail_setup
    ],
)
