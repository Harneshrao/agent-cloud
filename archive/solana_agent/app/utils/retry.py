"""
Retry utility using tenacity.

Usage:
    result = await with_retry(some_async_fn, arg1, arg2)
"""

import logging

from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

_RETRY_POLICY = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


async def with_retry(fn, *args, **kwargs):
    """
    Call `fn(*args, **kwargs)` with up to 3 attempts and exponential backoff.
    Re-raises the last exception if all attempts fail.
    """
    async for attempt in AsyncRetrying(**_RETRY_POLICY):
        with attempt:
            return await fn(*args, **kwargs)
