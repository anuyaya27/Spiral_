from app.services.parsing.generic import parse_generic_json
from app.services.parsing.imessage import parse_imessage_json
from app.services.parsing.types import ParsedChat
from app.services.parsing.whatsapp import parse_whatsapp_txt


def parse_chat_export(path: str, platform: str, timezone_name: str) -> ParsedChat:
    normalized = platform.lower()
    if normalized == "whatsapp":
        return parse_whatsapp_txt(path, timezone_name)
    if normalized == "imessage":
        return parse_imessage_json(path, timezone_name)
    if normalized == "generic":
        return parse_generic_json(path, timezone_name)
    raise ValueError(f"Unsupported platform: {platform}")

