from datetime import datetime, timedelta
import functools

# Code borrowed from : https://gist.github.com/Morreski/c1d08a3afa4040815eafd3891e16b945

def timed_cache(**timed_cache_kwargs):                                              
    """ Timed LRU Cache

    usage:
        @timed_cache(hours=1)
        def functionname(parameter):
            ....
    parameters:
        days, seconds, minutes, hours, weeks : Input to time-delta for specifying cache timeout
        maxsize: Max number of entries cached 

    This will cache the response from parameter where parameter hashed,
    subsequent calls with same parameter returns the cache
    """
    def _wrapper(f):
        maxsize = timed_cache_kwargs.pop('maxsize', 128)
        typed = timed_cache_kwargs.pop('typed', False)
        update_delta = timedelta(**timed_cache_kwargs)
        next_update = datetime.utcnow() - update_delta
        f = functools.lru_cache(maxsize=maxsize, typed=False)(f)

        @functools.wraps(f)
        def _wrapped(*args, **kwargs):
            nonlocal next_update
            now = datetime.utcnow()
            if now >= next_update:
                f.cache_clear()
                next_update = now + update_delta
            return f(*args, **kwargs)
        return _wrapped
    return _wrapper