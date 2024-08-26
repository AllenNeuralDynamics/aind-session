from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


def get_ttl_hash(seconds: float = 10 * 60) -> int:
    """Return the same value within `seconds` time period.

    - used to cache function results for a limited period of time

    From https://stackoverflow.com/a/55900800
    """
    return round(time.time() / seconds)
