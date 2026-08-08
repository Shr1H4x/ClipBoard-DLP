from clipboard_dlp.detector import detect_sensitive, summarize_detections


def _types(text):
    return sorted({d["type"] for d in detect_sensitive(text)})


def test_password_assignment_detected():
    assert "password" in _types("password: hunter2")
    assert "password" in _types("PASSWD = supersecret")
    assert "password" in _types("pwd=12345")


def test_password_prose_detected():
    assert "password" in _types("the password is hunter2")
    assert "password" in _types("password for portal -> abcdef")


def test_env_secret_detected():
    assert "env_secret" in _types("DB_PASSWORD=supersecret123")
    assert "env_secret" in _types("SECRET_KEY = x9f2k3")


def test_secret_key_detected():
    assert "secret_key" in _types("client_secret: abc123")
    assert "secret_key" in _types("auth_token = t0k3n!")


def test_otp_context_detected():
    assert "otp" in _types("Your verification code is 482913")
    assert "otp" in _types("OTP: 123456")
    assert "otp" in _types("one-time password 765432")


def test_pin_detected():
    assert "pin" in _types("PIN: 9876")
    assert "pin" in _types("pin is 112233")


def test_plain_numbers_not_otp():
    assert "otp" not in _types("In 2026 we ship v2")
    assert "pin" not in _types("call support at 555 1234")
    assert "otp" not in _types("postal code: 12345")


def test_bare_password_like_detected():
    assert "password_like" in _types("_@B4g@mZ$RfyE3N")
    assert "password_like" in _types("mypassword123")
    assert "password_like" in _types("secret_2024")
    assert "password_like" in _types("S3cret!2024")


def test_bare_text_not_password_like():
    assert "password_like" not in _types("correct horse battery staple")
    assert "password_like" not in _types("In 2026 we ship v2")
    assert "password_like" not in _types("COVID-19 update")
    assert "password_like" not in _types("user4@example.com")
    assert "password_like" not in _types("iPhone15ProMax")
    assert "password_like" not in _types("Windows11Update")
    assert "password_like" not in _types("Christmas2024")
    assert "password_like" not in _types("Thanks for the great meeting everyone")
    assert "password_like" not in _types("Version 2.0 is now available for download")


def test_jwt_does_not_match_ipv4():
    assert "ipv4" in _types("192.168.1.1")
    assert "jwt" not in _types("192.168.1.1")
    assert "jwt" in _types("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature")


def test_jwt_does_not_match_domains_or_versions():
    assert "jwt" not in _types("test.example.com")
    assert "jwt" not in _types("v1.2.3")
    assert "jwt" not in _types("www.example.co.uk")
    assert "jwt" not in _types("report.final.draft")


def test_summarize_detections_deduplicates():
    detections = [
        {"label": "Password"},
        {"label": "Password"},
        {"label": "OTP"},
    ]
    assert summarize_detections(detections) == "Password, OTP"
