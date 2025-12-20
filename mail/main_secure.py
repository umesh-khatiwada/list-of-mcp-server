import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gmail SMTP configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("GMAIL_USER", "lt@myboat2.com")
SMTP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_email(to_email, subject, body):
    """Send email using Gmail SMTP with App Password."""
    if not SMTP_PASSWORD:
        print("❌ Error: GMAIL_APP_PASSWORD not set in environment variables")
        print("Please create a .env file with GMAIL_APP_PASSWORD=your_app_password")
        return False

    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = SMTP_USER
        message["To"] = to_email
        message["Subject"] = subject

        # Add body to email
        message.attach(MIMEText(body, "plain"))

        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Enable TLS encryption
        server.login(SMTP_USER, SMTP_PASSWORD)

        # Send email
        text = message.as_string()
        server.sendmail(SMTP_USER, to_email, text)
        server.quit()

        print(f"✅ Email sent successfully to {to_email}!")
        return True

    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


if __name__ == "__main__":
    # Test email
    to_email = "umeshkhatiwada.uk@gmail.com"
    subject = "Test Email from Python (Secure Version)"
    body = """Hello!

This is a test email sent using Python and Gmail SMTP with secure credential handling.

Best regards,
Your Python Script"""

    send_email(to_email, subject, body)
