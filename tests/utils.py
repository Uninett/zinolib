import os
from pathlib import Path
from tempfile import mkstemp


__all__ = [
    'clean_textfile',
    'make_tmptextfile',
    'delete_tmpfile',
]


def clean_textfile(text):
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text


def make_tmptextfile(text, suffix, encoding='ascii'):
    text = clean_textfile(text)
    fd, filename = mkstemp(text=True, suffix=suffix)
    os.write(fd, bytes(text, encoding=encoding))
    return filename


def delete_tmpfile(filename):
    Path(filename).unlink(missing_ok=True)
