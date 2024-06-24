import functools
import hashlib
import platform
import socket


__all__ = [
    "windows_codepage_cp1252",
    "generate_authtoken",
    "enable_socket_keepalive",
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


def _enable_keepalive_linux(sock, after_idle_sec, interval_sec, max_fails):
    """Set TCP keepalive on an open socket.

    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 seconds
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)


def _enable_keepalive_osx(sock, after_idle_sec, interval_sec, max_fails):
    """Set TCP keepalive on an open socket.

    sends a keepalive ping once every 3 seconds (interval_sec)
    """
    # scraped from /usr/include, not exported by python's socket module
    TCP_KEEPALIVE = 0x10
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, interval_sec)


def _enable_keepalive_win(sock, after_idle_sec, interval_sec, max_fails):
    sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, after_idle_sec * 1000, interval_sec * 1000))


def enable_socket_keepalive(sock, after_idle_sec=60, interval_sec=60, max_fails=5):
    platforms = {
        "Linux": _enable_keepalive_linux,
        "Darwin": _enable_keepalive_osx,
        "Windows": _enable_keepalive_win,
    }
    if (plat := platform.system()) in platforms:
        return platforms[plat](sock, after_idle_sec, interval_sec, max_fails)
    raise RuntimeError('Unsupported platform: {}'.format(plat))
