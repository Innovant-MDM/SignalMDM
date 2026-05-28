import re
from typing import Any


def is_snake_case(value: str) -> bool:
    """Returns True if the string is in strict snake_case format (letters, numbers, underscores)."""
    if not value:
        return False
    return bool(re.match(r"^[a-z0-9]+(_[a-z0-9]+)*$", value))


def validate_email_format(value: Any) -> bool:
    """Validate standard email structure format."""
    if not value or not isinstance(value, str):
        return False
    # Standard email regex
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, value))


def validate_gstin_format(value: Any) -> bool:
    """Validate Indian GST number format (15 characters: 2 state code, 10 PAN, 1 entity, 1 blank, 1 check digit)."""
    if not value or not isinstance(value, str):
        return False
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, value.upper().strip()))


def validate_url_format(value: Any) -> bool:
    """Validate standard HTTP/HTTPS website URL structure."""
    if not value or not isinstance(value, str):
        return False
    pattern = r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"
    return bool(re.match(pattern, value.strip()))


def validate_sku_format(value: Any) -> bool:
    """Validate typical SKU/Product code format (alphanumeric, dashes, underscores)."""
    if not value:
        return False
    val_str = str(value).strip()
    return bool(re.match(r"^[a-zA-Z0-9-_]+$", val_str))


def validate_field_value(value: Any, validation_type: str) -> bool:
    """
    Validate a field's value based on its metadata validation rules.
    Allowed validation types: TEXT, EMAIL, PHONE, GSTIN, URL, SKU, STATE, COUNTRY, CITY
    """
    if value is None:
        return True  # nulls are allowed unless marked required at model level
        
    val_type = validation_type.upper()
    val_str = str(value).strip()
    
    if not val_str:
        return True
        
    if val_type == "EMAIL":
        return validate_email_format(val_str)
    elif val_type == "GSTIN":
        return validate_gstin_format(val_str)
    elif val_type == "URL":
        return validate_url_format(val_str)
    elif val_type == "SKU":
        return validate_sku_format(val_str)
    elif val_type == "PHONE":
        # At least 7 digits for phone validation
        digits = re.sub(r"\D", "", val_str)
        return len(digits) >= 7
        
    return True
