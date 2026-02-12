import logging


class PrivacyFilter(logging.Filter):
    """Drop dangerous fields from structured logs."""

    BLOCKED_KEYS = {"text", "message_text", "excerpt", "raw_content"}

    def filter(self, record: logging.LogRecord) -> bool:
        for key in self.BLOCKED_KEYS:
            if hasattr(record, key):
                setattr(record, key, "[REDACTED]")
        return True


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    root = logging.getLogger()
    root.addFilter(PrivacyFilter())

