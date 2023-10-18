# mypy: ignore-errors
try:
    from enum import StrEnum
except ImportError:
    # < Python 3.11
    from enum import Enum

    class StrEnum(str, Enum):
        __str__ = str.__str__

        def _generate_next_value_(name, start, count, last_values):
            """
            Return the lower-cased version of the member name.
            """
            return name.lower()


try:
    from tomllib import load as tomlload
except ImportError:
    try:
        from tomli import load as tomlload
    except ImportError:
        def tomlload(*args, **kwargs):
            raise ImportError("TOML library not available, TOML configuration impossible")


__all__ = ["StrEnum", "tomlload"]
