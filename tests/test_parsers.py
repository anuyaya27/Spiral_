from app.services.parsing import parse_chat_export


def test_parse_whatsapp():
    parsed = parse_chat_export("tests/fixtures/whatsapp_chat.txt", "whatsapp", "UTC")
    assert parsed.summary["message_count"] == 5
    assert len(parsed.participants) == 2


def test_parse_imessage():
    parsed = parse_chat_export("tests/fixtures/imessage_chat.json", "imessage", "UTC")
    assert parsed.summary["message_count"] == 4
    assert "Taylor" in parsed.participants


def test_parse_generic():
    parsed = parse_chat_export("tests/fixtures/generic_chat.json", "generic", "UTC")
    assert parsed.summary["message_count"] == 4
    assert parsed.messages[0].sender == "A"

