from core.logger import Logger

class SendEmailJob:
    def handle(self, data):
        email = data.get("email")
        subject = data.get("subject")
        body = data.get("body")
        Logger.info(f"Sending email to {email} with subject: '{subject}'...")
        # Simulate sending email
        Logger.info(f"Email successfully sent to {email}!")
