"""Email integration agent for Veronica."""

import os
import smtplib
import imaplib
import email
from email.message import EmailMessage
from .skills import AssistantContext, SkillResult

def is_email_request(message: str) -> bool:
    """Matcher for Email Integration requests."""
    lowered = message.lower().strip()
    return lowered.startswith(("send email", "read email", "check email", "check inbox", "read inbox"))

def handle_email_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to send or read emails via SMTP/IMAP."""
    lowered = message.lower().strip()
    
    email_user = os.getenv("EMAIL_USER", "").strip()
    email_pass = os.getenv("EMAIL_PASS", "").strip()
    
    if not email_user or not email_pass:
        return SkillResult(True, "Email Integration requires EMAIL_USER and EMAIL_PASS environment variables (Use an App Password!).")
        
    try:
        if lowered.startswith(("read", "check")):
            return _read_emails(email_user, email_pass)
        elif lowered.startswith("send"):
            # extremely simple parsing: "send email to X subject Y body Z"
            # Normally we would use an LLM router for this, but simple string matching works for the demo.
            return _send_email(message, email_user, email_pass)
            
        return SkillResult(True, "I didn't quite understand that email command.")
            
    except Exception as e:
        return SkillResult(True, f"Email operation failed: {e}")

def _read_emails(user: str, password: str) -> SkillResult:
    """Connect to IMAP and fetch the latest 3 unseen emails."""
    try:
        # Assuming Gmail for default IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, password)
        mail.select("inbox")
        
        status, messages = mail.search(None, 'UNSEEN')
        if status != "OK":
            return SkillResult(True, "Failed to search inbox.")
            
        email_ids = messages[0].split()
        if not email_ids:
            return SkillResult(True, "You have no unread emails!")
            
        # Get the latest 3
        latest_ids = email_ids[-3:]
        
        output = "📧 Latest Unread Emails:\n\n"
        for e_id in latest_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res == "OK":
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                subject = msg.get("Subject", "No Subject")
                sender = msg.get("From", "Unknown Sender")
                output += f"- From: {sender}\n  Subject: {subject}\n\n"
                
        mail.logout()
        return SkillResult(True, output.strip())
        
    except imaplib.IMAP4.error:
        return SkillResult(True, "IMAP Login failed. Did you use an App Password and enable IMAP in Gmail?")

def _send_email(message: str, user: str, password: str) -> SkillResult:
    """Connect to SMTP and send an email."""
    try:
        words = message.split()
        if "to" not in words:
            return SkillResult(True, "Please specify a recipient: 'send email to [address]'")
            
        to_idx = words.index("to")
        if to_idx + 1 >= len(words):
            return SkillResult(True, "Please specify an email address.")
            
        recipient = words[to_idx + 1]
        
        subject = "Message from Veronica"
        if "subject" in words:
            sub_idx = words.index("subject")
            body_idx = words.index("body") if "body" in words else len(words)
            subject = " ".join(words[sub_idx+1:body_idx])
            
        body = "Sent from Veronica AI."
        if "body" in words:
            body_idx = words.index("body")
            body = " ".join(words[body_idx+1:])
            
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = recipient
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        
        return SkillResult(True, f"✅ Email sent successfully to {recipient}!")
        
    except smtplib.SMTPAuthenticationError:
        return SkillResult(True, "SMTP Authentication failed. Did you use an App Password?")
    except Exception as e:
        return SkillResult(True, f"Failed to send email: {e}")
