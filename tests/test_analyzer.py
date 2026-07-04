from clipboard_dlp import analyzer


def test_btc_detected():
    text = "Send funds to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    res = analyzer.detect(text)
    assert "BTC_ADDRESS" in res["matches"]
    assert res["risk"] == "CRITICAL"


def test_entropy_detects_key_like():
    text = "sk-" + "A" * 40
    res = analyzer.detect(text)
    assert "API_KEY_LIKE" in res["matches"] or res["entropy"] > 4.5
    assert res["risk"] in ("HIGH", "CRITICAL")
