from app.services.analysis.types import DetectorResult


DETECTOR_WEIGHTS = {
    "initiation_imbalance": 1.0,
    "response_latency_asymmetry": 1.0,
    "warm_cold_cycles": 1.2,
    "boundary_setting_language": 1.2,
    "unresolved_future_talk": 0.8,
    "affection_distance_contradiction": 1.4,
}


def compute_confidence(message_count: int, covered_days: int, detector_results: list[DetectorResult]) -> float:
    sample_factor = min(message_count / 100, 1.0)
    coverage_factor = min(covered_days / 30, 1.0)
    non_zero = [r.score for r in detector_results if r.score > 0]
    consistency = min((len(non_zero) / max(len(detector_results), 1)) + (sum(non_zero) / max(len(non_zero), 1)) / 2, 1.0) if non_zero else 0.1
    return round((0.45 * sample_factor + 0.25 * coverage_factor + 0.30 * consistency), 3)


def compute_mixed_signal_index(detector_results: list[DetectorResult], confidence: float) -> tuple[float, dict]:
    weighted_sum = 0.0
    total_weight = 0.0
    breakdown: dict[str, dict] = {}
    for result in detector_results:
        weight = DETECTOR_WEIGHTS.get(result.detector, 1.0)
        total_weight += weight
        weighted_sum += result.score * weight
        breakdown[result.detector] = {"score": round(result.score, 3), "weight": weight}
    base = (weighted_sum / total_weight) if total_weight else 0.0
    index = round(base * confidence * 100, 2)
    return index, breakdown

