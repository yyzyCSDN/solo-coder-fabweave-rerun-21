from __future__ import annotations

from dataclasses import dataclass


def sample_indices(lot_size: int, sample_count: int) -> list[int]:
    if lot_size <= 0 or sample_count <= 0:
        raise ValueError("positive sizes required")
    n = min(lot_size, sample_count)
    if n == 1:
        return [0]
    span = lot_size - 1
    gaps = n - 1
    return [((2 * index * span) + gaps) // (2 * gaps) for index in range(n)]


@dataclass(frozen=True, slots=True)
class Wafer:
    wafer_id: str
    slot: int
    zone: str
    eligible: bool = True


def deterministic_sample(wafers: list[Wafer], sample_count: int, required_zones: set[str]) -> tuple[Wafer, ...]:
    if sample_count <= 0:
        raise ValueError("sample count must be positive")
    sorted_wafers = sorted(wafers, key=lambda wafer: (wafer.slot, wafer.wafer_id))
    eligible: list[Wafer] = []
    seen: dict[str, Wafer] = {}
    for wafer in sorted_wafers:
        if not wafer.eligible:
            continue
        previous = seen.get(wafer.wafer_id)
        if previous is not None:
            if previous != wafer:
                raise ValueError(f"duplicate wafer id with conflicting data: {wafer.wafer_id}")
            continue
        seen[wafer.wafer_id] = wafer
        eligible.append(wafer)

    if not eligible:
        raise ValueError("no eligible wafers")

    zones = {wafer.zone for wafer in eligible}
    missing = required_zones - zones
    if missing:
        raise ValueError(f"required zones unavailable: {', '.join(sorted(missing))}")
    if sample_count < len(required_zones):
        raise ValueError("sample count cannot cover required zones")
    if sample_count > len(eligible):
        raise ValueError("sample count exceeds unique eligible wafers")

    target = min(sample_count, len(eligible))
    if not required_zones:
        return tuple(eligible[index] for index in sample_indices(len(eligible), target))

    chosen_indices = set(sample_indices(len(eligible), target))
    for zone in sorted(required_zones):
        if any(eligible[index].zone == zone for index in chosen_indices):
            continue
        candidate_indices = [index for index, wafer in enumerate(eligible) if wafer.zone == zone]
        replaceable_indices = [
            index
            for index in chosen_indices
            if 0 < index < len(eligible) - 1 and eligible[index].zone not in required_zones
        ]
        replacement = min(
            replaceable_indices,
            key=lambda slot: (min(abs(slot - candidate) for candidate in candidate_indices), slot),
            default=None,
        )
        if replacement is None:
            raise ValueError("sample count cannot cover required zones and endpoints")
        chosen_indices.remove(replacement)
        chosen_indices.add(min(candidate_indices, key=lambda candidate: (abs(candidate - replacement), candidate)))
    return tuple(eligible[index] for index in sorted(chosen_indices))
