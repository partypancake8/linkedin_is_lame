"""
Debug-only unresolved field collector

This module provides read-only observability into unresolved fields that cause skips.
It does NOT change behavior, does NOT relax safety gates, and does NOT submit applications.

Usage:
    1. Enable with --debug-unresolved CLI flag
    2. Call record_unresolved_field() when resolution fails
    3. Call flush_unresolved_fields() on terminal states (SKIP/TEST_SUCCESS/FAILED/CANCELLED)

Output:
    debug_unresolved.jsonl - one JSON object per unresolved field
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional

_unresolved_buffer: List[Dict] = []


def record_unresolved_field(
    *,
    job_id: str,
    job_url: str,
    state_at_exit: str,
    skip_reason: str,
    field_type: str,
    question_text: str,
    options: Optional[List[str]],
    classification: str,
    tier: str,
    eligibility: bool,
    confidence: str,
    matched_key: Optional[str],
):
    """
    Record an unresolved field to the in-memory buffer.

    This is a side-effect only - does NOT change return values or behavior.

    Args:
        job_id: LinkedIn job ID
        job_url: Full job URL
        state_at_exit: State when resolution failed (e.g., RADIO_UNRESOLVED)
        skip_reason: Skip reason constant (e.g., unresolved_field)
        field_type: Field type (radio, select, text)
        question_text: Question/label text from UI
        options: List of available options (for radio/select) or None
        classification: Classification result (e.g., TIER1_WORK_AUTHORIZATION)
        tier: Tier level (tier-1, tier-2, skip, unknown)
        eligibility: Whether field was deemed eligible for automation
        confidence: Confidence level (high, medium, low, none)
        matched_key: Matched answer bank key or None
    """
    _unresolved_buffer.append(
        {
            "timestamp": datetime.now(ZoneInfo("America/Detroit")).isoformat(),
            "job_id": job_id,
            "job_url": job_url,
            "state_at_exit": state_at_exit,
            "skip_reason": skip_reason,
            "field_type": field_type,
            "question_text": question_text,
            "options": options,
            "classification": classification,
            "tier": tier,
            "eligible": eligibility,
            "confidence": confidence,
            "matched_key": matched_key,
        }
    )


def flush_unresolved_fields():
    """
    Flush all buffered unresolved fields to debug_unresolved.jsonl.

    This is called on terminal states only:
    - SKIP
    - TEST_SUCCESS
    - FAILED
    - CANCELLED

    Never called mid-run. Append-only. One JSON object per line.
    """
    if not _unresolved_buffer:
        return

    with open("debug_unresolved.jsonl", "a", encoding="utf-8") as f:
        for record in _unresolved_buffer:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    _unresolved_buffer.clear()
