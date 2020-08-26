import sys
import warnings
from functools import wraps


def deprecated(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(f'Function/method {func.__qualname__} is deprecated', category=DeprecationWarning)
        return func(*args, **kwargs)

    return wrapper
