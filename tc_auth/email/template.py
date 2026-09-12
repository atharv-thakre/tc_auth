
# ==========================================================
# HTML EMAIL TEMPLATES
# ==========================================================

def _otp_template(
    *,
    title: str,
    message: str,
    otp: str,
    expiry: int,
    magic_link: str | None = None,
):
    minutes = expiry // 60

    magic_button_html = ""
    if magic_link:
        magic_button_html = f"""
        <!-- MAGIC LINK BUTTON -->
        <div style="text-align: center; margin: 25px 0 15px 0;">
            <a href="{magic_link}" target="_blank" style="
                display: inline-block;
                padding: 14px 28px;
                background-color: #2563eb;
                color: #ffffff;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 15px;
                box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
            ">
                Click to Proceed
            </a>
        </div>
        <p style="text-align: center; margin: 0 0 20px 0; font-size: 12px; color: #6b7280;">
            Button not working? Copy and paste this link:<br>
            <a href="{magic_link}" style="color: #2563eb; word-break: break-all;">{magic_link}</a>
        </p>
        <div style="text-align: center; margin: 25px 0 15px 0; font-size: 12px; color: #9ca3af; letter-spacing: 1px;">
            — OR USE VERIFICATION CODE —
        </div>
        """

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>

<body style="
    margin: 0;
    padding: 0;
    background-color: #f4f6f8;
    font-family: Arial, Helvetica, sans-serif;
">

<table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td align="center" style="padding: 40px 15px;">

            <table
                width="100%"
                cellpadding="0"
                cellspacing="0"
                border="0"
                style="
                    max-width: 500px;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    border: 1px solid #e5e7eb;
                "
            >

                <!-- HEADER -->
                <tr>
                    <td style="
                        padding: 28px;
                        text-align: center;
                        background-color: #111827;
                        color: #ffffff;
                    ">
                        <h1 style="
                            margin: 0;
                            font-size: 24px;
                            font-weight: 700;
                        ">
                            Verification & Authentication
                        </h1>
                    </td>
                </tr>

                <!-- CONTENT -->
                <tr>
                    <td style="padding: 35px 30px;">

                        <h2 style="
                            margin: 0 0 15px 0;
                            color: #111827;
                            font-size: 20px;
                        ">
                            {title}
                        </h2>

                        <p style="
                            margin: 0 0 20px 0;
                            color: #4b5563;
                            font-size: 15px;
                            line-height: 1.6;
                        ">
                            {message}
                        </p>

                        {magic_button_html}

                        <!-- OTP -->
                        <div style="
                            text-align: center;
                            margin: 20px 0;
                        ">

                            <div style="
                                display: inline-block;
                                padding: 16px 32px;
                                background-color: #f3f4f6;
                                border: 1px solid #d1d5db;
                                border-radius: 10px;
                                letter-spacing: 8px;
                                font-size: 30px;
                                font-weight: 700;
                                color: #111827;
                            ">
                                {otp}
                            </div>

                        </div>

                        <p style="
                            margin: 0;
                            text-align: center;
                            color: #6b7280;
                            font-size: 14px;
                        ">
                            This code and link expire in
                            <strong>{minutes} minutes</strong>.
                        </p>

                        <p style="
                            margin-top: 25px;
                            color: #6b7280;
                            font-size: 13px;
                            line-height: 1.5;
                        ">
                            If you did not request this email, you can safely
                            ignore it.
                        </p>

                    </td>
                </tr>

                <!-- FOOTER -->
                <tr>
                    <td style="
                        padding: 20px 30px;
                        background-color: #f9fafb;
                        text-align: center;
                        border-top: 1px solid #e5e7eb;
                    ">
                        <p style="
                            margin: 0;
                            color: #9ca3af;
                            font-size: 12px;
                        ">
                            This is an automated message. Please do not reply.
                        </p>
                    </td>
                </tr>

            </table>

        </td>
    </tr>
</table>

</body>
</html>
"""


# ==========================================================
# VERIFY EMAIL TEMPLATE
# ==========================================================

def verify_email_template(
    *,
    otp: str,
    expiry: int,
    magic_link: str | None = None,
):
    return _otp_template(
        title="Verify your email",
        message=(
            "Use the button or verification code below to verify "
            "your email address and continue."
        ),
        otp=otp,
        expiry=expiry,
        magic_link=magic_link,
    )


# ==========================================================
# LOGIN OTP TEMPLATE
# ==========================================================

def login_otp_template(
    *,
    otp: str,
    expiry: int,
    magic_link: str | None = None,
):
    return _otp_template(
        title="Login verification",
        message=(
            "We received a request to sign in to your account. "
            "Click the button below or enter the code to complete your login."
        ),
        otp=otp,
        expiry=expiry,
        magic_link=magic_link,
    )


# ==========================================================
# SIGNUP OTP TEMPLATE
# ==========================================================

def signup_otp_template(
    *,
    otp: str,
    expiry: int,
    magic_link: str | None = None,
):
    return _otp_template(
        title="Complete your registration",
        message=(
            "Use the button or code below to confirm your "
            "email address and complete your account registration."
        ),
        otp=otp,
        expiry=expiry,
        magic_link=magic_link,
    )


# ==========================================================
# RESET PASSWORD TEMPLATE
# ==========================================================

def reset_password_template(
    *,
    otp: str,
    expiry: int,
    magic_link: str | None = None,
):
    return _otp_template(
        title="Reset your password",
        message=(
            "We received a request to reset your password. "
            "Click the button below or use the code to set a new password."
        ),
        otp=otp,
        expiry=expiry,
        magic_link=magic_link,
    )


# ==========================================================
# TEMPLATES COLLECTION
# ==========================================================

templates = {
    "signup": signup_otp_template,
    "login": login_otp_template,
    "reset": reset_password_template,
    "verify": verify_email_template,
}


