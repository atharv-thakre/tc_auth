
# ==========================================================
# HTML EMAIL TEMPLATES
# ==========================================================

def _otp_template(
    *,
    title: str,
    message: str,
    otp: str,
    expiry: int,
):
    minutes = expiry // 60

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
                            Verification Code
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
                            margin: 0 0 25px 0;
                            color: #4b5563;
                            font-size: 15px;
                            line-height: 1.6;
                        ">
                            {message}
                        </p>

                        <!-- OTP -->
                        <div style="
                            text-align: center;
                            margin: 30px 0;
                        ">

                            <div style="
                                display: inline-block;
                                padding: 18px 35px;
                                background-color: #f3f4f6;
                                border: 1px solid #d1d5db;
                                border-radius: 10px;
                                letter-spacing: 8px;
                                font-size: 32px;
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
                            This code expires in
                            <strong>{minutes} minutes</strong>.
                        </p>

                        <p style="
                            margin-top: 25px;
                            color: #6b7280;
                            font-size: 13px;
                            line-height: 1.5;
                        ">
                            If you did not request this code, you can safely
                            ignore this email.
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
):
    return _otp_template(
        title="Verify your email",
        message=(
            "Use the verification code below to verify "
            "your email address and continue."
        ),
        otp=otp,
        expiry=expiry,
    )


# ==========================================================
# LOGIN OTP TEMPLATE
# ==========================================================

def login_otp_template(
    *,
    otp: str,
    expiry: int,
):
    return _otp_template(
        title="Login verification",
        message=(
            "We received a request to sign in to your account. "
            "Use the code below to complete your login."
        ),
        otp=otp,
        expiry=expiry,
    )


# ==========================================================
# SIGNUP OTP TEMPLATE
# ==========================================================

def signup_otp_template(
    *,
    otp: str,
    expiry: int,
):
    return _otp_template(
        title="Complete your registration",
        message=(
            "Use the verification code below to confirm your "
            "email address and complete your account registration."
        ),
        otp=otp,
        expiry=expiry,
    )

# ==========================================================
# RESET PASSWORD TEMPLATE
# ==========================================================

def reset_password_template(
    *,
    otp: str,
    expiry: int,
):
    return _otp_template(
        title="Reset your password",
        message=(
            "We received a request to reset your password. "
            "Use the verification code below to set a new password."
        ),
        otp=otp,
        expiry=expiry,
    )

# ==========================================================
# TEMPLATES COLLECTION
# ==========================================================


templates = {
    "verify": verify_email_template,
    "verify_email": verify_email_template,
    "login": login_otp_template,
    "signup": signup_otp_template,
    "reset": reset_password_template,
    "reset_password": reset_password_template,
}

