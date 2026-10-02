"""Append-safe JSON decision history for the single-writer prototype."""

import json
import os
import tempfile
from pathlib import Path

from canonical_schema import CanonicalReviewDecision


def _with_normalized_fields(raw, normalized):
    # Keep unrecognized audit fields in comparisons, including nested mappings.
    if isinstance(raw, dict) and isinstance(normalized, dict):
        return {
            **raw,
            **{key: _with_normalized_fields(raw.get(key), value)
               for key, value in normalized.items()},
        }
    if isinstance(raw, list) and isinstance(normalized, list):
        return [_with_normalized_fields(old, new)
                for old, new in zip(raw, normalized)]
    return normalized


def _validate_decisions(records, label):
    if not isinstance(records, list):
        raise ValueError(f"{label} decisions must be a list.")
    indexed = {}
    for record in records:
        decision = CanonicalReviewDecision.model_validate(record)
        decision_id = decision.decision_id
        if decision_id in indexed:
            raise ValueError(f"Duplicate decision ID in {label}: {decision_id}")
        if decision.decision == "approve":
            if not decision.approved_canonical_id:
                raise ValueError(
                    f"Decision {decision_id}: approved decision requires "
                    "approved_canonical_id."
                )
            for mapping in decision.approved_official_mappings:
                if mapping.canonical_id != decision.approved_canonical_id:
                    raise ValueError(
                        f"Decision {decision_id}: mapping canonical ID "
                        "does not match approved canonical ID."
                    )
                if mapping.review_status != "approved":
                    raise ValueError(
                        f"Decision {decision_id}: approved mapping must have "
                        "review_status='approved'."
                    )
        # New-node domain/skill requirements remain enforced by Promotion,
        # which knows whether the canonical node already exists in baseline.
        indexed[decision_id] = _with_normalized_fields(
            record, decision.model_dump()
        )
    return indexed


def _atomic_write_json(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=path.name + ".", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        # Close the temporary file before replacing on Windows.
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def append_review_decisions(path, candidates):
    """Validate the complete batch before writing; preserve existing records."""
    path = Path(path)
    try:
        history = json.loads(path.read_text(encoding="utf-8"))
        exists = True
    except FileNotFoundError:
        history = {"prototype_version": "0.2", "decisions": []}
        exists = False
    if not isinstance(history, dict) or "decisions" not in history:
        raise ValueError("Decision log must be an object containing decisions.")

    existing = _validate_decisions(history["decisions"], "existing history")
    candidate_records = [
        item.model_dump() if isinstance(item, CanonicalReviewDecision) else item
        for item in candidates
    ]
    incoming = _validate_decisions(candidate_records, "candidate decisions")
    merged = list(history["decisions"])
    messages = []
    for decision_id, normalized in incoming.items():
        if decision_id in existing:
            if existing[decision_id] != normalized:
                raise ValueError(
                    f"Conflicting human review decision: {decision_id}. "
                    "Existing history must not be overwritten."
                )
            messages.append(f"SKIP identical decision: {decision_id}")
        else:
            merged.append(normalized)
            messages.append(f"ADD decision: {decision_id}")

    output = {**history, "decision_count": len(merged), "decisions": merged}
    if not exists or output != history:
        _atomic_write_json(path, output)
    for message in messages:
        print(message)
    return output
