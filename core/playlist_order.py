from __future__ import annotations


def build_reordered_ids(all_ids: list[str], moving_ids: list[str], target: int) -> list[str]:
    """Return a stable block move using an insertion boundary from the original list.

    ``target`` ranges from 0 (before the first row) through ``len(all_ids)``
    (after the last row).  Selected items keep their original relative order,
    including non-contiguous multi-selection.
    """
    normalized_all = [str(value) for value in all_ids]
    normalized_moving = [str(value) for value in moving_ids]
    if (
        not normalized_all
        or not normalized_moving
        or len(set(normalized_all)) != len(normalized_all)
        or len(set(normalized_moving)) != len(normalized_moving)
        or not set(normalized_moving).issubset(set(normalized_all))
    ):
        raise ValueError("Invalid playlist reorder data.")

    moving_set = set(normalized_moving)
    # Preserve playlist order even if a caller supplies selected IDs in another
    # order (for example, selectionModel enumeration order).
    ordered_moving = [item_id for item_id in normalized_all if item_id in moving_set]
    selected_rows = [index for index, item_id in enumerate(normalized_all) if item_id in moving_set]
    remaining = [item_id for item_id in normalized_all if item_id not in moving_set]
    boundary = max(0, min(len(normalized_all), int(target)))
    removed_before = sum(1 for row in selected_rows if row < boundary)
    insert_at = max(0, min(len(remaining), boundary - removed_before))
    return remaining[:insert_at] + ordered_moving + remaining[insert_at:]
