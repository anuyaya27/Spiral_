from collections import defaultdict

from app.services.analysis.types import DetectorResult


def run_detectors(features: list[dict]) -> list[DetectorResult]:
    return [
        initiation_imbalance(features),
        response_latency_asymmetry(features),
        warm_cold_cycles(features),
        boundary_setting_language(features),
        unresolved_future_talk(features),
        affection_distance_contradiction(features),
    ]


def initiation_imbalance(features: list[dict]) -> DetectorResult:
    starts = defaultdict(int)
    evidence: list[str] = []
    previous = None
    for row in sorted(features, key=lambda x: x["ts"]):
        if previous is None or (row["ts"] - previous["ts"]).total_seconds() > 6 * 3600:
            starts[row["sender_name"]] += 1
            evidence.append(row["id"])
        previous = row
    if not starts:
        return DetectorResult("initiation_imbalance", 0.0, "Not enough data.", [])
    values = sorted(starts.values(), reverse=True)
    score = (values[0] - values[-1]) / max(values[0], 1)
    return DetectorResult(
        "initiation_imbalance",
        max(0.0, min(score, 1.0)),
        "One participant initiates far more conversations than the other.",
        evidence[:10],
    )


def response_latency_asymmetry(features: list[dict]) -> DetectorResult:
    latency = defaultdict(list)
    evidence: list[str] = []
    previous = None
    for row in sorted(features, key=lambda x: x["ts"]):
        if previous and previous["sender_id"] != row["sender_id"]:
            minutes = (row["ts"] - previous["ts"]).total_seconds() / 60
            latency[row["sender_name"]].append(minutes)
            evidence.extend([previous["id"], row["id"]])
        previous = row
    if len(latency) < 2:
        return DetectorResult("response_latency_asymmetry", 0.0, "Not enough alternating replies.", [])
    averages = [sum(v) / len(v) for v in latency.values() if v]
    if len(averages) < 2:
        return DetectorResult("response_latency_asymmetry", 0.0, "Not enough latency data.", [])
    score = abs(max(averages) - min(averages)) / max(max(averages), 1.0)
    return DetectorResult(
        "response_latency_asymmetry",
        max(0.0, min(score, 1.0)),
        "One participant tends to respond much slower than the other.",
        list(dict.fromkeys(evidence))[:12],
    )


def warm_cold_cycles(features: list[dict]) -> DetectorResult:
    evidence: list[str] = []
    flips = 0
    for idx in range(1, len(features)):
        prev = features[idx - 1]
        curr = features[idx]
        warm_to_cold = prev["affection"] and (curr["avoidance"] or curr["sentiment"] < -0.2)
        cold_to_warm = prev["avoidance"] and (curr["affection"] or curr["sentiment"] > 0.4)
        if warm_to_cold or cold_to_warm:
            flips += 1
            evidence.extend([prev["id"], curr["id"]])
    score = min(flips / max(len(features) / 12, 1), 1.0)
    return DetectorResult(
        "warm_cold_cycles",
        score,
        "Detected alternating affectionate and distant behavior within short windows.",
        list(dict.fromkeys(evidence))[:12],
    )


def boundary_setting_language(features: list[dict]) -> DetectorResult:
    hits = [row["id"] for row in features if row["boundary"]]
    score = min(len(hits) / max(len(features) / 20, 1), 1.0)
    return DetectorResult(
        "boundary_setting_language",
        score,
        "Boundary-setting language appears repeatedly in the conversation.",
        hits[:12],
    )


def unresolved_future_talk(features: list[dict]) -> DetectorResult:
    evidence: list[str] = []
    unresolved = 0
    for idx, row in enumerate(features):
        if not row["future_talk"]:
            continue
        window = features[idx + 1 : idx + 25]
        followed_up = any(w["future_talk"] and w["sender_id"] != row["sender_id"] for w in window)
        if not followed_up:
            unresolved += 1
            evidence.append(row["id"])
    score = min(unresolved / max(len(features) / 30, 1), 1.0)
    return DetectorResult(
        "unresolved_future_talk",
        score,
        "Plans are suggested but not clearly confirmed later.",
        evidence[:12],
    )


def affection_distance_contradiction(features: list[dict]) -> DetectorResult:
    contradictions = 0
    evidence: list[str] = []
    for idx, row in enumerate(features):
        if row["sentiment"] > 0.4 or row["affection"]:
            for follow in features[idx + 1 : idx + 7]:
                if follow["avoidance"] or follow["sentiment"] < -0.2:
                    contradictions += 1
                    evidence.extend([row["id"], follow["id"]])
                    break
    score = min(contradictions / max(len(features) / 20, 1), 1.0)
    return DetectorResult(
        "affection_distance_contradiction",
        score,
        "Positive wording often appears near avoidant behavior.",
        list(dict.fromkeys(evidence))[:12],
    )

