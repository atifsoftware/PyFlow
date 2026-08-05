"""
core/mailer.py
===============
SMTP-ভিত্তিক Email সিস্টেম। কোনো external library ছাড়াই
Python stdlib (smtplib, email.mime) দিয়ে বাস্তবায়িত।

ব্যবহার:
    from core.mailer import Mailer

    # Simple text email
    Mailer.send(
        to="user@example.com",
        subject="স্বাগতম!",
        body="আপনাকে স্বাগতম।"
    )

    # HTML Template email
    Mailer.send(
        to="user@example.com",
        subject="পাসওয়ার্ড রিসেট",
        view="emails.reset_password",
        data={"user": user, "link": reset_url}
    )
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os


class Mailer:
    """
    SMTP Mailer facade। config/config.py-এর MAIL_* মান দিয়ে কাজ করে।
    
    .env-এ সেট করুন:
        MAIL_HOST=smtp.gmail.com
        MAIL_PORT=587
        MAIL_USERNAME=you@gmail.com
        MAIL_PASSWORD=yourpassword
        MAIL_ENCRYPTION=tls     # tls | ssl | none
        MAIL_FROM_ADDRESS=you@gmail.com
        MAIL_FROM_NAME=PyFlow App
    """

    @classmethod
    def _get_config(cls) -> dict:
        from config.config import get_config
        cfg = get_config()
        return {
            "host":       cfg.get("MAIL_HOST", "smtp.mailtrap.io"),
            "port":       int(cfg.get("MAIL_PORT", 587)),
            "username":   cfg.get("MAIL_USERNAME", ""),
            "password":   cfg.get("MAIL_PASSWORD", ""),
            "encryption": cfg.get("MAIL_ENCRYPTION", "tls").lower(),
            "from_addr":  cfg.get("MAIL_FROM_ADDRESS", "noreply@pyflow.dev"),
            "from_name":  cfg.get("MAIL_FROM_NAME", "PyFlow App"),
        }

    @classmethod
    def send(
        cls,
        to: str | list,
        subject: str,
        body: str = None,
        view: str = None,
        data: dict = None,
        attachments: list = None,
        config: dict = None,
    ) -> bool:
        """
        Email পাঠায়। view দিলে template render করে HTML email পাঠায়।

        Args:
            to:          Email ঠিকানা (একটি string বা list)
            subject:     Email বিষয়
            body:        Plain text body (view না দিলে)
            view:        Template path যেমন "emails.welcome" → app/views/emails/welcome.html
            data:        Template-এ পাঠানো context dict
            attachments: [(filename, bytes_or_path), ...] ফাইল সংযুক্তি
            config:      কাস্টম SMTP config dict (না দিলে .env থেকে নেবে)

        Returns:
            bool: সফল হলে True
        """
        cfg = config or cls._get_config()

        if isinstance(to, str):
            to = [to]

        # HTML body তৈরি
        html_body = None
        if view:
            html_body = cls._render_view(view, data or {})
        if not body and html_body:
            # HTML থেকে simple plain text বের করা (fallback)
            import re
            body = re.sub(r"<[^>]+>", "", html_body).strip()

        # MIME message তৈরি
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{cfg['from_name']} <{cfg['from_addr']}>"
        msg["To"]      = ", ".join(to)

        if body:
            msg.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Attachments যোগ করা
        for attachment in (attachments or []):
            fname, fdata = attachment
            if isinstance(fdata, str) and os.path.isfile(fdata):
                with open(fdata, "rb") as f:
                    fdata = f.read()
            part = MIMEBase("application", "octet-stream")
            part.set_payload(fdata)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={fname}")
            msg.attach(part)

        # SMTP connection ও send
        return cls._smtp_send(cfg, to, msg.as_string())

    @classmethod
    def _smtp_send(cls, cfg: dict, recipients: list, raw_message: str) -> bool:
        host = cfg["host"]
        port = cfg["port"]
        username = cfg["username"]
        password = cfg["password"]
        encryption = cfg["encryption"]
        from_addr = cfg["from_addr"]

        try:
            if encryption == "ssl":
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(host, port, context=context)
            else:
                server = smtplib.SMTP(host, port)
                if encryption == "tls":
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()

            if username and password:
                server.login(username, password)

            server.sendmail(from_addr, recipients, raw_message.encode("utf-8"))
            server.quit()
            return True
        except Exception as exc:
            import logging
            logging.getLogger("pyflow.mailer").error(f"Email পাঠাতে সমস্যা: {exc}")
            return False

    @classmethod
    def _render_view(cls, view_path: str, data: dict) -> str:
        """Template render করে HTML string রিটার্ন করে"""
        from core.view import View
        try:
            return View.render(view_path, data)
        except Exception as exc:
            import logging
            logging.getLogger("pyflow.mailer").warning(f"Email template render error: {exc}")
            return f"<p>Template render হয়নি: {view_path}</p>"

    @classmethod
    def raw(cls, to: str | list, subject: str, html: str, config: dict = None) -> bool:
        """Raw HTML string দিয়ে email পাঠায়"""
        return cls.send(to=to, subject=subject, body=None, view=None, data=None, config=config,
                        **{"_raw_html": html})

    @classmethod
    def queue(cls, **kwargs) -> bool:
        """Background queue-এ email পাঠানোর জন্য (Queue সিস্টেম ব্যবহার করে)"""
        try:
            from core.queue import Queue
            Queue.push("SendEmailJob", kwargs)
            return True
        except Exception:
            # Queue না থাকলে সরাসরি পাঠানো
            return cls.send(**kwargs)
