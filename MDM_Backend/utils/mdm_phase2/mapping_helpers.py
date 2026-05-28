from typing import Any, Optional


def get_nested_value(data: dict[str, Any], path: str, delimiter: str = ".") -> Any:
    """
    Safely retrieves a value from a nested dictionary using a delimited path.
    Example: get_nested_value({"user": {"profile": {"name": "Alice"}}}, "user.profile.name") -> "Alice"
    """
    if not data or not path:
        return None
        
    parts = path.split(delimiter)
    current: Any = data
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
            
    return current
