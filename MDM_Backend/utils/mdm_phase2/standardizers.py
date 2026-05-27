from typing import Any


def standardize_value(value: Any, mappings: dict[str, Any]) -> Any:
    """
    Standardizes a value using a look-up dictionary.
    Performs case-insensitive checks on key matches for maximum flexibility.
    """
    if value is None:
        return value
        
    val_str = str(value).strip()
    
    # Try direct exact lookup
    if val_str in mappings:
        return mappings[val_str]
        
    # Try case-insensitive lookup
    val_lower = val_str.lower()
    for k, v in mappings.items():
        if k.lower() == val_lower:
            return v
            
    # Return as-is if no match is found
    return value
