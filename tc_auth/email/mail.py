import smtplib
import socket
from email.message import EmailMessage
from urllib.parse import quote_plus
from ..email.template import templates
from ..exceptions.error import (
    AuthError,
    EmailNotConfiguredError,
    EmailSendError,
    InvalidConfigError,
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

    @property
    def is_configured(self) -> bool:
        return bool(
            self.host
            and self.port
            and self.username
            and self.password
            and self.sender
        )

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
        if not host or not isinstance(host, str) or not host.strip():
            raise InvalidConfigError("Email", "Email SMTP host is required and must be a non-empty string")

        if not isinstance(port, int) or port < 1 or port > 65535:
            raise InvalidConfigError("Email", "Email SMTP port must be an integer between 1 and 65535")

        if not username or not isinstance(username, str) or not username.strip():
            raise InvalidConfigError("Email", "Email SMTP username is required and must be a non-empty string")

        if not password or not isinstance(password, str) or not password.strip():
            raise InvalidConfigError("Email", "Email SMTP password is required and must be a non-empty string")

        if not sender or not isinstance(sender, str) or not sender.strip() or "@" not in sender:
            raise InvalidConfigError("Email", "Email sender address is required and must be a valid email string")

        self.host = host.strip()
        self.port = port

        self.username = username.strip()
        self.password = password.strip()

        self.sender = sender.strip()
        self.sender_name = sender_name.strip() if isinstance(sender_name, str) and sender_name.strip() else None

        self.use_tls = bool(use_tls)

        return {
            "success": True,
            "message": "Email service configured successfully",
        }


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
        if not self.is_configured:
            raise EmailNotConfiguredError("Email service is not configured (missing host, port, username, password, or sender)")

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

        return {
            "success": True,
            "message": f"Email sent successfully to {to}",
        }

    # ==========================================================
    # OTP
    # ==========================================================

    def send_otp(
        self,
        *,
        email: str,
        purpose: str,
        expiry: int = 300,
        frontend_url: str | None = None,
        backend_url: str | None = None,
        magic_link: str | None = None,
    ):
        if not self.is_configured:
            raise EmailNotConfiguredError("Email service is not configured (missing host, port, username, password, or sender)")

        if not purpose or not isinstance(purpose, str):
            raise InvalidEmailPurposeError(str(purpose))

        normalized_purpose = purpose.strip().lower()
        template = templates.get(normalized_purpose)
        if template is None:
            raise InvalidEmailPurposeError(purpose)

        result = self.otp.create(
            identifier=email,
            purpose=normalized_purpose,
            expiry=expiry,
        )

        otp_code = result["otp"]

        if not magic_link and frontend_url:
            base = (backend_url or "").rstrip("/")
            if base.endswith("/tc-auth"):
                base = base[:-8]
            magic_link = f"{base}/tc-auth/link/{normalized_purpose}?email={quote_plus(email)}&otp={otp_code}&frontend_url={quote_plus(frontend_url)}"

        body = template(
            otp=otp_code,
            expiry=expiry,
            magic_link=magic_link,
        )

        subject_map = {
            "login": "Sign-In Link & Code" if magic_link else "Login Verification Code",
            "signup": "Sign-Up Verification Link & Code" if magic_link else "Sign-Up Verification Code",
            "reset": "Password Reset Link & Code" if magic_link else "Password Reset Code",
            "verify": "Email Verification Link & Code" if magic_link else "Email Verification Code",
        }
        subject = subject_map.get(normalized_purpose, "Verification Code")

        self.send(
            to=email,
            subject=subject,
            body=body,
            html=True,
        )

        return {
            "expires_at": result["expires_at"],
        }

    # ==========================================================
    # MAGIC LINK
    # ==========================================================

    def send_magic_link(
        self,
        *,
        email: str,
        purpose: str,
        frontend_url: str,
        backend_url: str | None = None,
        expiry: int = 300,
        magic_link: str | None = None,
    ):
        return self.send_otp(
            email=email,
            purpose=purpose,
            expiry=expiry,
            frontend_url=frontend_url,
            backend_url=backend_url,
            magic_link=magic_link,
        )

    # ==========================================================
    # VERIFY EMAIL
    # ==========================================================

    def send_verify_email(
        self,
        *,
        email: str,
        frontend_url: str | None = None,
    ):
        return self.send_otp(
            email=email,
            purpose="verify",
            frontend_url=frontend_url,
        )

    # ==========================================================
    # LOGIN OTP
    # ==========================================================

    def send_login_otp(
        self,
        email: str,
        frontend_url: str | None = None,
    ):
        return self.send_otp(
            email=email,
            purpose="login",
            frontend_url=frontend_url,
        )

    # ==========================================================
    # SIGNUP OTP
    # ==========================================================

    def send_signup_otp(
        self,
        email: str,
        frontend_url: str | None = None,
    ):
        return self.send_otp(
            email=email,
            purpose="signup",
            frontend_url=frontend_url,
        )

    # ==========================================================
    # RESET PASSWORD OTP
    # ==========================================================

    def send_reset_otp(
        self,
        email: str,
        frontend_url: str | None = None,
    ):
        return self.send_otp(
            email=email,
            purpose="reset",
            frontend_url=frontend_url,
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
                    timeout=10,
                )
                smtp.starttls()
            else:
                smtp = smtplib.SMTP_SSL(
                    self.host,
                    int(self.port),
                    timeout=10,
                )

            smtp.login(
                self.username,
                self.password,
            )
            return smtp
        except smtplib.SMTPAuthenticationError as e:
            raise EmailSendError(f"SMTP authentication failed (invalid username or password): {str(e)}")
        except smtplib.SMTPConnectError as e:
            raise EmailSendError(f"Failed to connect to SMTP server '{self.host}:{self.port}': {str(e)}")
        except (socket.timeout, TimeoutError):
            raise EmailSendError(f"Connection to SMTP server '{self.host}:{self.port}' timed out")
        except socket.gaierror as e:
            raise EmailSendError(f"Failed to resolve SMTP server host '{self.host}': {str(e)}")
        except smtplib.SMTPException as e:
            raise EmailSendError(f"SMTP error occurred: {str(e)}")
        except Exception as e:
            raise EmailSendError(f"Failed to connect to SMTP server: {str(e)}")