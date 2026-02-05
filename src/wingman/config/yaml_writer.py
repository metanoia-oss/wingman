"""Safe YAML read-modify-write for configuration files."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def read_yaml(path: Path) -> dict:
    """Read a YAML file and return its contents as a dict.

    Returns an empty dict if the file doesn't exist or is malformed.
    """
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except yaml.YAMLError as e:
        logger.warning(f"Malformed YAML in {path}: {e}")
        return {}
    except OSError as e:
        logger.warning(f"Cannot read {path}: {e}")
        return {}


def write_yaml(path: Path, data: dict) -> None:
    """Write a dict to a YAML file, preserving readable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def set_nested_value(data: dict, dotted_key: str, value: str) -> dict:
    """
    Set a value in a nested dict using dotted key notation.

    Example:
        set_nested_value({}, "openai.model", "gpt-4-turbo")
        -> {"openai": {"model": "gpt-4-turbo"}}

    Attempts to coerce value to int/float/bool if appropriate.
    """
    keys = dotted_key.split(".")
    current = data

    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[keys[-1]] = _coerce_value(value)
    return data


def get_nested_value(data: dict, dotted_key: str) -> object:
    """
    Get a value from a nested dict using dotted key notation.

    Returns None if the key doesn't exist.
    """
    keys = dotted_key.split(".")
    current = data

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]

    return current


def _coerce_value(value: str) -> object:
    """Coerce a string value to the appropriate Python type."""
    # Booleans
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False

    # Integers
    try:
        return int(value)
    except ValueError:
        pass

    # Floats
    try:
        return float(value)
    except ValueError:
        pass

    return value
