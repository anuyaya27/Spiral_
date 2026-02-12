from datetime import datetime, timezone

from app.services.analysis.detectors import run_detectors


def test_detectors_return_expected_shapes():
    rows = [
        {"id": "1", "ts": datetime(2025, 1, 1, 10, tzinfo=timezone.utc), "sender_id": "a", "sender_name": "A", "text": "love you", "sentiment": 0.8, "affection": True, "avoidance": False, "hedge": False, "boundary": False, "future_talk": True},
        {"id": "2", "ts": datetime(2025, 1, 1, 20, tzinfo=timezone.utc), "sender_id": "b", "sender_name": "B", "text": "maybe later, busy", "sentiment": -0.3, "affection": False, "avoidance": True, "hedge": True, "boundary": False, "future_talk": False},
        {"id": "3", "ts": datetime(2025, 1, 2, 9, tzinfo=timezone.utc), "sender_id": "a", "sender_name": "A", "text": "let's do friday", "sentiment": 0.2, "affection": False, "avoidance": False, "hedge": False, "boundary": False, "future_talk": True},
        {"id": "4", "ts": datetime(2025, 1, 4, 9, tzinfo=timezone.utc), "sender_id": "b", "sender_name": "B", "text": "not ready", "sentiment": -0.2, "affection": False, "avoidance": True, "hedge": False, "boundary": True, "future_talk": False},
    ]
    results = run_detectors(rows)
    assert len(results) == 6
    for detector in results:
        assert 0.0 <= detector.score <= 1.0
        assert isinstance(detector.explanation, str)

