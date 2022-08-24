import bisect
import string
import time

_UNITS_MULTIPLIER = 1000
_UNITS_EXPONENTS_MAPPING = {
    "b": 0,
    "k": 1,
    "m": 2,
    "g": 3,
    "t": 4,
    "p": 5,
    "e": 6,
    "z": 7,
    "y": 8,
}

_UNITS = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
_SIZES = tuple(1024 ** i for i, _ in enumerate(_UNITS))

_REL_TO_ABS_TIME_MULTIPLIER_MAPPING = {
    "d": 86_400,
    "w": 86_400 * 7,
    "m": 86_400 * 30,
    "y": 86_400 * 365,
}

_UNPRINTABLES = "".join(chr(c) for c in range(128) if chr(c) not in string.printable)
_INVALID_PATHNAME_CHARS = "".join((_UNPRINTABLES, ':*?"<>|\t\n\r\x0b\x0c'))


def Bytes_from_value_and_unit(value: float, unit: str = "B") -> int:
    """
    Converts VALUE UNIT size pair to Bytes:
        20, M -> 20_000_000 Bytes
        30, G -> 31_457_280 Bytes
        ...

    Parameters
    -----------
        value (float):
            Value of size.
        unit (str):
            Unit. Defaults to B (Bytes).
            Possible values are B, K, M, G, T, P, E, Z, Y.
    """
    return value * (_UNITS_MULTIPLIER ** _UNITS_EXPONENTS_MAPPING[unit.lower()])


def get_value_and_unit_from_Bytes(Bytes: int, round_to: int = 2) -> tuple[int, str]:
    """
    Converts number of Bytes to appropriate higher unit. One unit is 1024 of the
    smaller unit:
        1024 Bytes -> 1 KiB
        1024 KiB -> 1 MiB
        1024 MiB -> 1 GiB
        1024 GiB -> 1 TiB
        ...

    Parameters
    -----------
        Bytes (int):
            Number of Bytes.
        round_to (int, optional):
            Maximum number of numbers after the decimal point. Defaults to 2.

    Returns
    --------
        tuple[
            (int):
                Value of Bytes converted to an appropriate higher unit.
            (str):
                Unit of value.
        ]
    """
    i = max(bisect.bisect(_SIZES, Bytes) - 1, 0)
    unit = _UNITS[i]
    size = round(Bytes / _SIZES[i], round_to)

    return size, unit


def relative_time_to_timestamp(rel_time: str) -> float:
    """
    Converts relative date to UNIX timestamp.
    Takes inputs in <amount><period> format, possible periods:
        - d:
            For x days ago.
        - w:
            For x weeks ago.
        - m:
            For x months ago.
        - y:
            For x years ago.

    Parameters
    -----------
        rel_time:
            Relative time.

    Returns
    --------
        float:
            Relative time converted to UNIX timestamp.
    """
    *amount, period = rel_time
    amount = int("".join(amount))
    return time.time() - (amount * _REL_TO_ABS_TIME_MULTIPLIER_MAPPING[period])


def validate_pathname(pathname: str) -> str:
    """
    Replaces invalid characters in a pathname with `_`.

    Parameters
    -----------
        pathname (str):
            Pathname to be validated.

    Returns
    --------
        str:
            Validated pathname.
    """
    new_pathname = ""
    for char in pathname:
        if char in _INVALID_PATHNAME_CHARS:
            new_pathname = "".join((new_pathname, "-"))
        else:
            new_pathname = "".join((new_pathname, char))

    return new_pathname
