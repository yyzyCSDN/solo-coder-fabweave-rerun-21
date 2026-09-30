from __future__ import annotations

from dataclasses import dataclass


def sample_indices(lot_size: int, sample_count: int) -> list[int]:
    if lot_size <= 0 or sample_count <= 0:
        raise ValueError("positive sizes required")
    n = min(lot_size, sample_count)
    if n == 1:
        return [0]
    # Evenly spread positions that always cover both ends: when the lot does
    # not divide evenly, truncating (i*lot_size/n) would silently drop the
    # tail wafer. Pin the endpoints at 0 and lot_size-1 and round each
    # interior position (half up) toward its nearest slot.
    last = lot_size - 1
    span = n - 1
    return [
        last
        if index == span
        else (2 * index * last + span) // (2 * span)
        for index in range(n)
    ]


@dataclass(frozen=True, slots=True)
class Wafer:
    wafer_id: str
    slot: int
    zone: str
    eligible: bool = True


def deterministic_sample(wafers: list[Wafer], sample_count: int, required_zones: set[str]) -> tuple[Wafer, ...]:
    if sample_count <= 0:
        raise ValueError("sample count must be positive")
    # Deduplicate by wafer id first; otherwise the same wafer appearing twice
    # upstream could be selected twice and the sample count would not match
    # the distinct evidence list at the quality gate.
    unique: dict[str, Wafer] = {}
    for wafer in wafers:
        if wafer.eligible and wafer.wafer_id not in unique:
            unique[wafer.wafer_id] = wafer
    eligible = sorted(unique.values(), key=lambda wafer: (wafer.slot, wafer.wafer_id))
    zones = {wafer.zone for wafer in eligible}
    missing = required_zones - zones
    if missing:
        raise ValueError(f"required zones unavailable: {', '.join(sorted(missing))}")
    if sample_count < len(required_zones):
        raise ValueError("sample count cannot cover required zones")

    target = min(sample_count, len(eligible))
    chosen: list[Wafer] = []
    chosen_ids: set[str] = set()

    def add(wafer: Wafer) -> bool:
        if wafer.wafer_id in chosen_ids:
            return False
        chosen.append(wafer)
        chosen_ids.add(wafer.wafer_id)
        return True

    # Required zones are anchored at their median wafer so coverage cannot
    # depend on how evenly the sparse fill happens to fall.
    for zone in sorted(required_zones):
        candidates = [wafer for wafer in eligible if wafer.zone == zone]
        add(candidates[len(candidates) // 2])

    # Fill the remaining slots sparsely over the full eligible sequence so
    # the head and tail wafers stay covered, with a sequential fallback that
    # preserves coverage if an anchor already occupies a sparse position.
    positions = sample_indices(len(eligible), target)
    for position in positions:
        if len(chosen) >= target:
            break
        add(eligible[position])
    for wafer in eligible:
        if len(chosen) >= target:
            break
        add(wafer)

    return tuple(sorted(chosen, key=lambda wafer: (wafer.slot, wafer.wafer_id)))
