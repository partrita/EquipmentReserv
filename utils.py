import random
import string
from typing import Iterator

def get_filename(filename: str) -> str:
    """Generates a filename with a random suffix."""
    suffix = "".join(random.choices(string.digits, k=19))
    return f"{filename.upper()}{suffix}"

def myrange(start: float, end: float, step: float) -> Iterator[float]:
    """Yields values from start to end with a given step."""
    current = start
    while current < end:
        yield current
        current += step