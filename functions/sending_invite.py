import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_invitation_email(to_email: str, role: str):
    subject = "You're Invited to SID Document Evaluator"
    body = f"""
    Hello,

    You have been invited to join SID Document Evaluator as a {role}.
    
    Click the link below to accept your invitation (this will be added later):

    [ACCEPT INVITE LINK]

    Best regards,  
    Document Evaluator Team
    """

    msg = MIMEMultipart()
    msg["From"] = SMTP_USERNAME
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
            print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        raise
