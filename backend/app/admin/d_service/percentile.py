"""percentile(): the value below which p percent of the values fall (nearest-rank method).
percentile([...], 95) is the "p95" on the monitoring page."""

import math


def percentile(values: list[int], p: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]
