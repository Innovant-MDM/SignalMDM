"""
signalmdm/utils/sanitize.py
-----------------------------
Centralized input sanitization, injection detection, and data quality
validation for all service layers.

Security scope:
  - SQL injection pattern detection
  - XSS / script injection detection
  - LIKE wildcard escaping (prevents wildcard-bomb performance attacks)
  - Input length enforcement
  - Slug / code format validation (allowlist character sets)
  - JSON depth and key-count limits
  - IP address format validation

Data quality scope:
  - Empty row detection
  - Missing value detection per field
  - Within-batch duplicate detection
  - Cross-run duplicate result tracking

Usage:
    from signalmdm.utils.sanitize import (
        sanitize_slug, sanitize_string, sanitize_search,
        sanitize_config_json, sanitize_ip,
        validate_row_data, BulkInsertResult,
    )
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# SQL injection keyword / syntax detection
_SQL_INJECTION_RE = re.compile(
    r"""
    (\b(
        SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|
        EXEC|EXECUTE|UNION|SCRIPT|DECLARE|CAST|CONVERT|
        XP_|SP_|XP_CMDSHELL|
        SLEEP\s*\(|WAITFOR\s+DELAY|BENCHMARK\s*\(|
        PG_SLEEP|PG_DUMP|PG_RESTORE|
        OR\s+1\s*=\s*1|AND\s+1\s*=\s*1|
        OR\s+'[^']*'\s*=\s*'[^']*'|
        1\s*=\s*1|1\s*=\s*0
    )\b)
    | ('--|";\s*--|';\s*DROP|\-\-\s*$|/\*|\*/)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# XSS / script injection detection
_SCRIPT_RE = re.compile(
    r"""
    (<\s*script|</\s*script|javascript\s*:|vbscript\s*:|
     on\w+\s*=\s*["']?|<\s*iframe|<\s*object|<\s*embed|
     <\s*form|eval\s*\(|document\s*\.|window\s*\.|
     alert\s*\(|confirm\s*\(|prompt\s*\(|
     expression\s*\(|url\s*\()
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Slug: lowercase alphanumeric, underscores, hyphens only
_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9_\-]*$')

# Valid IPv4 / IPv6 (simple format check, not full CIDR)
_IP_RE = re.compile(
    r'^(\d{1,3}\.){3}\d{1,3}$'      # IPv4
    r'|^[0-9a-fA-F:]+$'             # IPv6 (simplified)
    r'|^::1$'                        # loopback
)

# Fields whose content we treat as "null / missing" at data quality scan time
_NULL_LIKE_VALUES = frozenset({
    "", "null", "none", "n/a", "na", "nil", "#n/a", "undefined",
    "unknown", "-", "--", "0", "false",
})

# Maximum limits
_MAX_SLUG_LEN        = 100
_MAX_NAME_LEN        = 200
_MAX_SEARCH_LEN      = 150
_MAX_PERFORMED_BY    = 150
_MAX_TRACE_ID        = 100
_MAX_ENTITY_NAME     = 100
_MAX_CONFIG_KEYS     = 60
_MAX_CONFIG_DEPTH    = 5
_MAX_ROWS_PER_BATCH  = 50_000    # Hard ceiling on single-call bulk inserts
_MAX_FIELD_VALUE_LEN = 5_000     # Single field value in raw data


# ---------------------------------------------------------------------------
# LIKE wildcard escape
# ---------------------------------------------------------------------------

def escape_like(value: str) -> str:
    """
    Escape LIKE wildcards so user search terms are treated as literals.

    Prevents wildcard-bomb patterns like "%" which match everything, or
    repeated "_" patterns that can force full-table scans.
    """
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


# ---------------------------------------------------------------------------
# Injection scanning
# ---------------------------------------------------------------------------

def scan_for_injection(value: str, field_name: str = "input") -> None:
    """
    Raise ValueError if *value* contains SQL injection or XSS patterns.

    NOTE: Do NOT call this on raw business data rows (raw_data JSONB) — those
    are stored verbatim and queried via parameterized ORM calls, so they cannot
    cause SQL injection regardless of content.  Call this only on internal
    control-plane fields (codes, names, slugs, search terms).
    """
    if _SQL_INJECTION_RE.search(value):
        logger.warning("[sanitize] SQL-injection pattern detected in field=%s", field_name)
        raise ValueError(f"Disallowed SQL pattern in '{field_name}'. Remove SQL keywords or operators.")
    if _SCRIPT_RE.search(value):
        logger.warning("[sanitize] Script-injection pattern detected in field=%s", field_name)
        raise ValueError(f"Script content is not permitted in '{field_name}'.")


# ---------------------------------------------------------------------------
# Generic string sanitizer
# ---------------------------------------------------------------------------

def sanitize_string(
    value: str | None,
    field_name: str,
    max_length: int = _MAX_NAME_LEN,
    required: bool = False,
    scan_injection: bool = True,
) -> str:
    """
    Strip, length-check, and optionally scan a string field.

    Returns the cleaned string (empty string if not required and blank).
    Raises ValueError for invalid values.
    """
    if value is None or str(value).strip() == "":
        if required:
            raise ValueError(f"'{field_name}' is required and cannot be empty.")
        return ""
    cleaned = str(value).strip()
    if len(cleaned) > max_length:
        raise ValueError(
            f"'{field_name}' exceeds the maximum length of {max_length} characters "
            f"(got {len(cleaned)})."
        )
    if scan_injection:
        scan_for_injection(cleaned, field_name)
    return cleaned


# ---------------------------------------------------------------------------
# Slug / code sanitizer
# ---------------------------------------------------------------------------

def sanitize_slug(value: str, field_name: str = "source_code") -> str:
    """
    Validate and normalize a slug-style code field.

    Rules: lowercase alphanumeric, underscores, hyphens; must start with
    an alphanumeric character; max 100 chars.

    Raises ValueError on any violation.
    """
    if not value or not value.strip():
        raise ValueError(f"'{field_name}' is required.")
    cleaned = value.strip().lower()
    if len(cleaned) > _MAX_SLUG_LEN:
        raise ValueError(f"'{field_name}' must be ≤ {_MAX_SLUG_LEN} characters.")
    if not _SLUG_RE.match(cleaned):
        raise ValueError(
            f"'{field_name}' may only contain lowercase letters, digits, underscores, "
            "and hyphens, and must start with a letter or digit. "
            f"Got: {cleaned!r}"
        )
    # Still scan for injection (e.g. SQL embedded in otherwise valid slug characters)
    scan_for_injection(cleaned, field_name)
    return cleaned


# ---------------------------------------------------------------------------
# Search term sanitizer
# ---------------------------------------------------------------------------

def sanitize_search(value: str | None, max_length: int = _MAX_SEARCH_LEN) -> str | None:
    """
    Sanitize a user-supplied search string.

    - Strips whitespace.
    - Truncates to *max_length*.
    - Scans for injection patterns.
    - Escapes LIKE wildcards (%, _) so the term is treated as a literal substring.

    Returns None if the input is blank.
    """
    if not value or not value.strip():
        return None
    cleaned = value.strip()[:max_length]
    scan_for_injection(cleaned, "search")
    return escape_like(cleaned)


# ---------------------------------------------------------------------------
# config_json sanitizer
# ---------------------------------------------------------------------------

def sanitize_config_json(
    config: dict | None,
    max_keys: int = _MAX_CONFIG_KEYS,
    max_depth: int = _MAX_CONFIG_DEPTH,
) -> dict:
    """
    Validate a JSON configuration dict.

    Checks:
      1. Must be a dict (not a list or primitive).
      2. Must not exceed *max_keys* top-level keys.
      3. Nesting must not exceed *max_depth* levels.
      4. No key or string value may contain injection patterns.

    Returns the original dict (no modification) if valid.
    Raises ValueError on any violation.
    """
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise ValueError("'config_json' must be a JSON object (key-value dict), not a list or primitive.")
    if len(config) > max_keys:
        raise ValueError(f"'config_json' has {len(config)} keys; maximum allowed is {max_keys}.")
    _check_json_depth(config, max_depth, current_depth=1)
    _scan_json_node(config, path="config_json")
    return config


def _check_json_depth(node: Any, max_depth: int, current_depth: int) -> None:
    if current_depth > max_depth:
        raise ValueError(
            f"'config_json' nesting depth exceeds the maximum of {max_depth} levels."
        )
    if isinstance(node, dict):
        for v in node.values():
            _check_json_depth(v, max_depth, current_depth + 1)
    elif isinstance(node, list):
        for item in node:
            _check_json_depth(item, max_depth, current_depth + 1)


def _scan_json_node(node: Any, path: str) -> None:
    if isinstance(node, str):
        scan_for_injection(node, path)
    elif isinstance(node, dict):
        for k, v in node.items():
            scan_for_injection(str(k), f"{path}.key")
            _scan_json_node(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _scan_json_node(item, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# IP address sanitizer
# ---------------------------------------------------------------------------

def sanitize_ip(ip: str | None) -> str | None:
    """
    Validate an IP address string.

    Returns the stripped IP if valid, or None if invalid / absent.
    Never raises — silently drops bad values so audit logging is not blocked.
    """
    if not ip:
        return None
    stripped = ip.strip()
    if not stripped or not _IP_RE.match(stripped):
        logger.debug("[sanitize] Invalid IP address dropped: %r", stripped)
        return None
    return stripped


# ---------------------------------------------------------------------------
# Entity name sanitizer (for audit_log entity_name field)
# ---------------------------------------------------------------------------

def sanitize_entity_name(value: str) -> str:
    """Validate an entity table name used in audit logging."""
    cleaned = sanitize_string(value, "entity_name", max_length=_MAX_ENTITY_NAME, required=True)
    # Entity names should only contain alphanumeric, underscores
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', cleaned):
        raise ValueError(
            f"'entity_name' must start with a letter and contain only letters, digits, "
            f"and underscores. Got: {cleaned!r}"
        )
    return cleaned


# ---------------------------------------------------------------------------
# Data quality result types
# ---------------------------------------------------------------------------

@dataclass
class RowQualityIssue:
    """A single data quality issue found in a raw data row."""
    row_index: int
    issue_type: str   # EMPTY_ROW | MISSING_VALUES | WITHIN_BATCH_DUPLICATE
    details: str

    def to_dict(self) -> dict:
        return {
            "row_index": self.row_index,
            "issue_type": self.issue_type,
            "details": self.details,
        }


@dataclass
class BulkInsertResult:
    """
    Result of a bulk_insert_raw_records call, including data quality metrics.

    Callers should log or surface `.summary()` alongside the run's record_count.
    """
    inserted_count: int = 0
    total_received: int = 0
    within_batch_duplicates_skipped: int = 0
    cross_run_duplicates_detected: int = 0
    empty_rows_skipped: int = 0
    rows_with_missing_values: int = 0
    quality_issues: list[RowQualityIssue] = dc_field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.quality_issues)

    def summary(self) -> dict:
        return {
            "total_received": self.total_received,
            "inserted_count": self.inserted_count,
            "within_batch_duplicates_skipped": self.within_batch_duplicates_skipped,
            "cross_run_duplicates_detected": self.cross_run_duplicates_detected,
            "empty_rows_skipped": self.empty_rows_skipped,
            "rows_with_missing_values": self.rows_with_missing_values,
            "quality_issue_count": len(self.quality_issues),
        }


# ---------------------------------------------------------------------------
# Row-level data quality validation
# ---------------------------------------------------------------------------

def validate_row_data(
    row: dict[str, Any],
    row_index: int,
) -> list[RowQualityIssue]:
    """
    Check a single parsed data row for quality issues.

    NOTE: We intentionally do NOT scan raw business data values for SQL/script
    injection — that data is never concatenated into queries (all ORM /
    parameterized), and stripping/rejecting business data would corrupt it.
    We only check structural quality: emptiness and missing values.

    Returns a list of RowQualityIssue (empty list = clean row).
    """
    issues: list[RowQualityIssue] = []

    if not row:
        issues.append(RowQualityIssue(
            row_index=row_index,
            issue_type="EMPTY_ROW",
            details="Row is completely empty (no fields).",
        ))
        return issues

    # Detect missing / null-like values per field
    missing_fields: list[str] = []
    for field_name, value in row.items():
        if value is None:
            missing_fields.append(str(field_name))
        elif isinstance(value, str) and value.strip().lower() in _NULL_LIKE_VALUES:
            missing_fields.append(str(field_name))

    if missing_fields:
        # Report first 15 missing fields to avoid huge messages
        sample = missing_fields[:15]
        suffix = f" (+{len(missing_fields) - 15} more)" if len(missing_fields) > 15 else ""
        issues.append(RowQualityIssue(
            row_index=row_index,
            issue_type="MISSING_VALUES",
            details=f"Empty/null fields: {', '.join(sample)}{suffix}.",
        ))

    # Guard against excessively large individual field values
    oversized = [
        k for k, v in row.items()
        if isinstance(v, str) and len(v) > _MAX_FIELD_VALUE_LEN
    ]
    if oversized:
        issues.append(RowQualityIssue(
            row_index=row_index,
            issue_type="OVERSIZED_FIELD",
            details=f"Fields exceed {_MAX_FIELD_VALUE_LEN} chars: {', '.join(str(f) for f in oversized[:5])}.",
        ))

    return issues


def validate_batch_size(rows: list[dict[str, Any]]) -> None:
    """Raise ValueError if the batch exceeds the hard ceiling."""
    if len(rows) > _MAX_ROWS_PER_BATCH:
        raise ValueError(
            f"Batch size {len(rows)} exceeds the maximum of {_MAX_ROWS_PER_BATCH} rows per call. "
            "Split the file into smaller chunks."
        )
