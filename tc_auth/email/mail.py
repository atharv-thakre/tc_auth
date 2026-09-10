import smtplib
from email.message import EmailMessage
from ..email.template import templates
from ..exceptions.error import (
    EmailNotConfiguredError,
    EmailSendError,
    InvalidEmailPurposeError,
)


class EmailService:
    def __init__(self, otp_service):
        self.otp = otp_service

        self.host = None
        self.port = None

        self.username = None
        self.password = None

        self.sender = None
        self.sender_name = None

        self.use_tls = True

    def load(self):
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "sender": self.sender,
            "sender_name": self.sender_name,
            "use_tls": self.use_tls,
        }

    # ==========================================================
    # CONFIGURE
    # ==========================================================

    def config(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        sender_name: str | None = None,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port

        self.username = username
        self.password = password

        self.sender = sender
        self.sender_name = sender_name

        self.use_tls = use_tls

    # ==========================================================
    # SEND
    # ==========================================================

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
    ):
        if not self.sender:
            raise EmailNotConfiguredError("Email sender address is not configured")

        if not to or not isinstance(to, str) or not to.strip():
            raise EmailSendError("Recipient email address 'to' is required")

        message = EmailMessage()

        if self.sender_name:
            message["From"] = f"{self.sender_name} <{self.sender}>"
        else:
            message["From"] = self.sender

        message["To"] = to.strip()
        message["Subject"] = subject

        if html:
            message.add_alternative(
                body,
                subtype="html",
            )
        else:
            message.set_content(body)

        smtp = None
        try:
            smtp = self._connect()
            smtp.send_message(message)
        except (EmailNotConfiguredError, EmailSendError):
            raise
        except Exception as e:
            raise EmailSendError(f"Failed to send email to {to}: {str(e)}")
        finally:
            if smtp is not None:
                try:
                    smtp.quit()
                except Exception:
                    pass

    # ==========================================================
    # OTP
    # ==========================================================

    def send_otp(
        self,
        *,
        email: str,
        purpose: str,
        expiry: int = 300,
    ):
        template = templates.get(purpose)
        if template is None:
            raise InvalidEmailPurposeError(purpose)

        result = self.otp.create(
            identifier=email,
            purpose=purpose,
            expiry=expiry,
        )

        body = template(
            otp=result["otp"],
            expiry=expiry,
        )

        self.send(
            to=email,
            subject="Verification Code",
            body=body,
            html=True,
        )

        return {
            "expires_at": result["expires_at"],
        }

    # ==========================================================
    # VERIFY EMAIL
    # ==========================================================

    def send_verify_email(
        self,
        *,
        email: str,
    ):
        return self.send_otp(
            email=email,
            purpose="verify_email",
        )

    # ==========================================================
    # LOGIN OTP
    # ==========================================================

    def send_login_otp(
        self,
        email: str,
    ):
        return self.send_otp(
            email=email,
            purpose="login",
        )

    # ==========================================================
    # SIGNUP OTP
    # ==========================================================

    def send_signup_otp(
        self,
        email: str,
    ):
        return self.send_otp(
            email=email,
            purpose="signup",
        )

    # ==========================================================
    # PRIVATE
    # ==========================================================

    def _connect(self):
        if not self.host or not self.port or not self.username or not self.password:
            raise EmailNotConfiguredError(
                "Email service host, port, username, or password is not configured"
            )

        try:
            if self.use_tls:
                smtp = smtplib.SMTP(
                    self.host,
                    int(self.port),
                )
                smtp.starttls()
            else:
                smtp = smtplib.SMTP_SSL(
                    self.host,
                    int(self.port),
                )

            smtp.login(
                self.username,
                self.password,
            )
            return smtp
        except smtplib.SMTPAuthenticationError as e:
            raise EmailSendError(f"SMTP authentication failed: {str(e)}")
        except smtplib.SMTPException as e:
            raise EmailSendError(f"SMTP error occurred: {str(e)}")
        except Exception as e:
            raise EmailSendError(f"Failed to connect to SMTP server: {str(e)}")