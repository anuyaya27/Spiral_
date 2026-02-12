from collections import defaultdict

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

AFFECTION_MARKERS = {"love", "miss you", "babe", "baby", "xo", "❤️", "😘", "😍", "sweetheart"}
AVOIDANCE_MARKERS = {"busy", "later", "idk", "i don't know", "can't", "cannot", "maybe", "not sure", "rain check"}
HEDGE_MARKERS = {"maybe", "kinda", "kind of", "unsure", "perhaps", "possibly"}
BOUNDARY_MARKERS = {"i can't", "not ready", "too much", "need space", "can't do this", "i need time"}
FUTURE_MARKERS = {"let's", "we should", "next week", "sometime", "plan", "trip", "dinner", "see you"}

analyzer = SentimentIntensityAnalyzer()


def _contains_any(text: str, lexicon: set[str]) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in lexicon)


def extract_message_features(messages: list[dict]) -> list[dict]:
    results: list[dict] = []
    for item in messages:
        text = item["text"]
        sentiment = analyzer.polarity_scores(text)["compound"] if text else 0.0
        results.append(
            {
                **item,
                "sentiment": sentiment,
                "affection": _contains_any(text, AFFECTION_MARKERS),
                "avoidance": _contains_any(text, AVOIDANCE_MARKERS),
                "hedge": _contains_any(text, HEDGE_MARKERS),
                "boundary": _contains_any(text, BOUNDARY_MARKERS),
                "future_talk": _contains_any(text, FUTURE_MARKERS),
            }
        )
    return results


def build_timeline_metrics(features: list[dict]) -> dict:
    if not features:
        return {}
    per_day: dict[str, int] = defaultdict(int)
    initiation_counts: dict[str, int] = defaultdict(int)
    response_by_sender: dict[str, list[float]] = defaultdict(list)
    engagement_shift: list[dict] = []

    features = sorted(features, key=lambda x: x["ts"])
    previous = None
    for idx, row in enumerate(features):
        day_key = row["ts"].date().isoformat()
        per_day[day_key] += 1

        if previous is None or (row["ts"] - previous["ts"]).total_seconds() > 6 * 3600:
            initiation_counts[row["sender_name"]] += 1

        if previous and previous["sender_id"] != row["sender_id"]:
            response_by_sender[row["sender_name"]].append((row["ts"] - previous["ts"]).total_seconds() / 60.0)
        previous = row

        if idx >= 9:
            window = features[idx - 9 : idx + 1]
            engagement_shift.append(
                {
                    "end_ts": row["ts"].isoformat(),
                    "avg_sentiment": sum(w["sentiment"] for w in window) / len(window),
                    "message_count": len(window),
                }
            )

    response_stats = {
        sender: {
            "avg_minutes": sum(values) / len(values),
            "median_minutes": sorted(values)[len(values) // 2],
            "count": len(values),
        }
        for sender, values in response_by_sender.items()
        if values
    }
    return {
        "messages_per_day": per_day,
        "messages_per_week": _aggregate_by_week(per_day),
        "response_time_stats": response_stats,
        "initiation_counts": initiation_counts,
        "streaks": _streaks(per_day),
        "engagement_shifts": engagement_shift,
    }


def _aggregate_by_week(per_day: dict[str, int]) -> dict[str, int]:
    weekly: dict[str, int] = defaultdict(int)
    for day_key, count in per_day.items():
        year, week, _ = __import__("datetime").datetime.fromisoformat(day_key).isocalendar()
        weekly[f"{year}-W{week:02d}"] += count
    return weekly


def _streaks(per_day: dict[str, int]) -> dict:
    days = sorted(per_day.keys())
    if not days:
        return {"longest_daily_streak": 0}
    longest = current = 1
    from datetime import datetime, timedelta

    previous = datetime.fromisoformat(days[0]).date()
    for day in days[1:]:
        current_day = datetime.fromisoformat(day).date()
        if current_day - previous == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
        previous = current_day
    return {"longest_daily_streak": longest}

