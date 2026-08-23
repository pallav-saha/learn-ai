"""
Shared utilities - retry logic for API calls.

Any script can import this to get automatic retries on LLM API failures.
"""

import time
import functools


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator that retries a function if it raises an exception.
    
    - max_retries: how many times to retry before giving up
    - delay: seconds to wait between retries (doubles each time)
    
    Usage:
        @retry_on_failure(max_retries=3, delay=1.0)
        def my_api_call():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"   ⚠️  Attempt {attempt} failed: {e}")
                        print(f"   🔄 Retrying in {current_delay:.1f}s... ({max_retries - attempt} retries left)")
                        time.sleep(current_delay)
                        current_delay *= 2  # Exponential backoff
                    else:
                        print(f"   ❌ All {max_retries} attempts failed.")

            raise last_exception

        return wrapper
    return decorator
