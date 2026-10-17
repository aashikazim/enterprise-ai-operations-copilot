import smtplib
import ssl

from app.db.database import get_settings

settings = get_settings()

try:
    with smtplib.SMTP(
        settings.smtp_host,
        587,
        timeout=20,
    ) as server:
        print("1. Connected")

        code, _ = server.ehlo()
        print("2. EHLO:", code)

        code, _ = server.starttls(
            context=ssl.create_default_context()
        )
        print("3. STARTTLS:", code)

        code, _ = server.ehlo()
        print("4. Post-TLS EHLO:", code)

        print(
            "5. SMTP AUTH supported:",
            server.has_extn("auth")
        )

        server.login(
            settings.smtp_username,
            settings.smtp_password,
        )
        print("6. Authentication successful")

except smtplib.SMTPAuthenticationError as e:
    print("Authentication rejected:", e.smtp_code)

except smtplib.SMTPServerDisconnected:
    print("SMTP connection unexpectedly closed")

except Exception as e:
    print("Error type:", type(e).__name__)