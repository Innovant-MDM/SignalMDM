import re
from datetime import datetime
from typing import Any, Optional


def transform_trim(value: Any) -> Any:
    """Trim whitespace from string values."""
    if isinstance(value, str):
        return value.strip()
    return value


def transform_uppercase(value: Any) -> Any:
    """Convert string to uppercase."""
    if isinstance(value, str):
        return value.upper()
    return value


def transform_lowercase(value: Any) -> Any:
    """Convert string to lowercase."""
    if isinstance(value, str):
        return value.lower()
    return value


def transform_title_case(value: Any) -> Any:
    """Convert string to title case."""
    if isinstance(value, str):
        return value.title()
    return value


def transform_remove_special_chars(value: Any) -> Any:
    """Remove special characters, leaving only alphanumeric and spaces."""
    if isinstance(value, str):
        return re.sub(r"[^a-zA-Z0-9\s]", "", value)
    return value


def transform_regex_replace(value: Any, pattern: str, replacement: str) -> Any:
    """Replace occurrences matching regex pattern with replacement string."""
    if isinstance(value, str):
        try:
            return re.sub(pattern, replacement, value)
        except Exception:
            return value
    return value


def transform_normalize_phone(value: Any, default_country: Optional[str] = None) -> Any:
    """
    Cleans phone numbers, removing common characters like spaces, dashes, parentheses.
    Keeps leading '+' if present.
    """
    if not value:
        return value
    val_str = str(value).strip()
    is_plus = val_str.startswith("+")
    # Leave only digits
    digits = re.sub(r"\D", "", val_str)
    if not digits:
        return ""
    
    prefix = "+" if is_plus else ""
    return f"{prefix}{digits}"


def transform_normalize_date(value: Any, output_format: str = "%Y-%m-%d") -> Any:
    """
    Normalize date strings to standard format (default YYYY-MM-DD).
    Attempts common parser formats.
    """
    if not value:
        return value
    val_str = str(value).strip()
    
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y",
        "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ",
        "%b %d, %Y", "%d %b %Y"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime(output_format)
        except ValueError:
            continue
            
    # Return as-is if parsing fails
    return value


def transform_normalize_country(value: Any) -> Any:
    """Clean country string, uppercase it, and trim whitespace."""
    if isinstance(value, str):
        return value.strip().upper()
    return value


def apply_transformation_chain(value: Any, chain: list[dict[str, Any]]) -> Any:
    """
    Apply a sequence of transformations to a value based on a list of configs.
    Each config contains: {'type': 'TRIM' | 'UPPERCASE' | ..., 'config': {...}}
    """
    current_value = value
    for step in chain:
        t_type = step.get("type", "").upper()
        cfg = step.get("config", {})
        
        try:
            if t_type == "TRIM":
                current_value = transform_trim(current_value)
            elif t_type == "UPPERCASE":
                current_value = transform_uppercase(current_value)
            elif t_type == "LOWERCASE":
                current_value = transform_lowercase(current_value)
            elif t_type == "TITLE_CASE":
                current_value = transform_title_case(current_value)
            elif t_type == "REMOVE_SPECIAL_CHARS":
                current_value = transform_remove_special_chars(current_value)
            elif t_type == "REGEX_REPLACE":
                pat = cfg.get("pattern", "")
                rep = cfg.get("replacement", "")
                if pat:
                    current_value = transform_regex_replace(current_value, pat, rep)
            elif t_type == "NORMALIZE_PHONE":
                current_value = transform_normalize_phone(current_value, cfg.get("default_country"))
            elif t_type == "NORMALIZE_DATE":
                fmt = cfg.get("output_format", "%Y-%m-%d")
                current_value = transform_normalize_date(current_value, fmt)
            elif t_type == "NORMALIZE_COUNTRY":
                current_value = transform_normalize_country(current_value)
        except Exception:
            # Degrade gracefully
            continue
            
    return current_value
