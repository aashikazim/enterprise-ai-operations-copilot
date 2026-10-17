# backend/app/services/email_service.py

import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode

from app.db.database import get_settings


def send_invitation_email(
    recipient_email: str,
    token: str,
) -> None:
    settings = get_settings()

    if not all([
        settings.smtp_username,
        settings.smtp_password,
        settings.smtp_from_email,
    ]):
        raise RuntimeError("SMTP configuration is incomplete")

    query = urlencode({"token": token})
    invitation_url = f"{settings.invitation_base_url}?{query}"

    message = EmailMessage()
    message["Subject"] = "Invitation to Enterprise AI Operations Copilot"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient_email

    message.set_content(
        "You have been invited to Enterprise AI Operations Copilot.\n\n"
        f"Accept your invitation:\n{invitation_url}\n\n"
        "This invitation expires in 24 hours and can only be used once.\n"
        "If you did not expect this invitation, ignore this email."
    )

    context = ssl.create_default_context()

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=30,
    ) as server:
        print("SMTP: TCP connected")

        server.ehlo()
        print("SMTP: EHLO successful")

        server.starttls(context=context)
        print("SMTP: TLS established")

        server.ehlo()
        print("SMTP: Post-TLS EHLO successful")

        server.login(
            settings.smtp_username,
            settings.smtp_password,
        )
        print("SMTP: Authentication successful")

        server.send_message(message)
        print("SMTP: Email sent successfully")