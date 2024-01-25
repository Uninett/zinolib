import functools
import hashlib


__all__ = [
    "windows_codepage_cp1252",
    "generate_authtoken",
]


def windows_codepage_cp1252(error):
    """Windows Codepage 1252 decoder fallback

    This function could be used as a failback for UnicodeEncodeError to fail
    back to windows codepage 1252 decoding when eg. utf-8 failes

    All valid windows codepage 1252 elements will be returned with their
    representative unicode characters and failes back to unicode unknown char
    when no valid character is found

    All illegal characters are replaced with unicode 0xFFFD
    """

    # This only works on UnicodeDecodeError, will not work on encoding
    if not isinstance(error, UnicodeDecodeError):
        raise error

    # 0xFFFD is the unicode char for illegal character.
    # these characters are not an valid printable cp1252 character

    cp1252_map = [
        0x20AC, 0xFFFD, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021,  # 0x80-0x87
        0x02c6, 0x2030, 0x0160, 0x2039, 0x0152, 0xFFFD, 0x017d, 0xFFFD,  # 0x88-0x8F
        0xFFFD, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014,  # 0x90-0x97
        0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0xFFFD, 0x017E, 0x0178   # 0x98-0x9F
    ]  # fmt: skip

    result = []
    for i in range(error.start, error.end):
        byte = error.object[i]

        if byte >= 0x80 and byte <= 0x9F:
            # We try to use windows codepage 1252 on this char
            result.append(chr(cp1252_map[byte - 0x80]))

        else:
            # This looks like a valid latin-1 char
            # It correspons to the same unicode char
            result.append(chr(0x00 + byte))

    return "".join(result), error.end


def generate_authtoken(challenge, password):
    "Combine Password and authChallenge from Ritz to make authToken"

    raw_token = "%s %s" % (challenge, password)
    token = hashlib.sha1(raw_token.encode("UTF-8")).hexdigest()
    return token


def log_exception_with_params(logger, reraise=True, return_value=None):
    """Log the params and exception if the wrapped function fails

    If ``reraise`` is False, return ``return_value`` instead of reraising the
    exception.
    """
    def inner(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            try:
                result = function(*args, **kwargs)
                return result
            except Exception as e:
                params = f'args={args} kwargs={kwargs}'
                funcname = function.__name__
                logger.exception('"%s" failed with: %s\n%s', funcname, params, e)
                if reraise:
                    raise
                return return_value
        return wrapper
    return inner
