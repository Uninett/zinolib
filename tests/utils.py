import os
from pathlib import Path
from tempfile import mkstemp


__all__ = [
    'clean_textfile',
    'make_tmptextfile',
    'delete_tmpfile',
    'executor',
]


def clean_textfile(text):
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text


def make_tmptextfile(text, suffix, prefix=None, encoding='ascii'):
    text = clean_textfile(text)
    fd, filename = mkstemp(text=True, suffix=suffix, prefix=prefix)
    os.write(fd, bytes(text, encoding=encoding))
    return filename


def delete_tmpfile(filename):
    Path(filename).unlink(missing_ok=True)


def executor(client):
    d = {
        "user testuser 7f53cac4ffa877616b8472d3b33a44cbba1907ad  -\r\n": ["200 ok\r\n"],
        "user auth-failure 7f53cac4ffa877616b8472d3b33a44cbba1907ad  -\r\n": [
            "500 Authentication failure\r\n"
        ],
        "user illegal-first-response 85970fa23a2f5aa06c22b60f04013fe072319ebd  -\r\n": [
            "something-gurba-happened"
        ],
        "user no_login_response 87101b4944f4200fce90f519ddae5eacffeeadf6  -\r\n": [""],
        "caseids\r\n": [
            "304 list of active cases follows, terminated with '.'\r\n",
            "32802\r\n34978\r\n.\r\n",
        ],
        "getattrs 32802\r\n": [
            "303 simple attributes follow, terminated with '.'\r\n",
            "state: working\r\nrouter: uninett-gsw2\r\ntype: bgp\r\nopened: 1524465142\r\nremote-addr: 2001:700:0:4515::5:11\r\nid: 32802\r\npeer-uptime: 0\r\nupdated: 1533116751\r\npolladdr: 127.0.0.1\r\npriority: 100\r\nbgpOS: down\r\nbgpAS: halted\r\nremote-AS: 64666\r\nlastevent: peer is admin turned off\r\n.\r\n",
        ],
        "getattrs 34978\r\n": [
            "303 simple attributes follow, terminated with '.'\r\n",
            "router: bergen-sw1\r\nstate: working\r\ntype: alarm\r\nalarm-count: 1\r\nopened: 1529156235\r\nalarm-type: yellow\r\nid: 34978\r\nupdated: 1529156235\r\npolladdr: 127.0.0.1\r\npriority: 100\r\nlastevent: alarms went from 0 to 1\r\n.\r\n",
        ],
        "getattrs 40959\r\n": [
            "303 simple attributes follow, terminated with '.'\r\n",
            "state: open\r\nrouter: oslo-gw1\r\ntype: bgp\r\nopened: 1539480952\r\nremote-addr: 193.108.152.34\r\nid: 40959\r\npeer-uptime: 503\r\nupdated: 1539485757\r\npolladdr: 128.39.0.1\r\npriority: 500\r\nbgpOS: established\r\nremote-AS: 21357\r\nbgpAS: running\r\nlastevent: peer was reset (now up)\r\n.\r\n",
        ],
        "gethist 40959\r\n": [
            "301 history follows, terminated with '.'\r\n",
            "1539480952 state change embryonic -> open (monitor)\r\n1539509123 runarb\r\n Testmelding ifra pyRitz\r\n \r\n.\r\n",
        ],
        "getlog 40959\r\n": [
            "300 log follows, terminated with '.'\r\n",
            "1539480952 oslo-gw1 peer 193.108.152.34 AS 21357 was reset (now up)\r\n1539484557 oslo-gw1 peer 193.108.152.34 AS 21357 was reset (now up)\r\n1539485757 oslo-gw1 peer 193.108.152.34 AS 21357 was reset (now up)\r\n.\r\n",
        ],
        "addhist 40959  -\r\n": [
            "302 please provide new history entry, termiate with '.'\r\n"
        ],
        "Testmelding ifra pyRitz\r\n\r\n.\r\n": ["200 ok\r\n"],
        "setstate 40959 open\r\n": ["200 ok\r\n"],
        "setstate 40959 working\r\n": ["200 ok\r\n"],
        "setstate 40959 waiting\r\n": ["200 ok\r\n"],
        "setstate 40959 confirm-wait\r\n": ["200 ok\r\n"],
        "setstate 40959 ignored\r\n": ["200 ok\r\n"],
        "setstate 40959 closed\r\n": ["200 ok\r\n"],
        "setstate 40960 open\r\n": ["500 Cannot reopen closed event 40960\r\n"],
        "clearflap uninett-tor-sw3 707\r\n": ["200 ok\r\n"],
        "pollrtr uninett-tor-sw3": ["200 ok\r\n"],
        "pollintf uninett-tor-sw3 707": ["200 ok\r\n"],
        "ntie 909e90c2eda89a09819ee7fe9b3f67cadb31449f\r\n": ["200 ok\r\n"],
        "ntie xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\r\n": [
            "500 Could not find your notify socket\r\n"
        ],
    }

    client.send("200 2f88fe9d496b1c1a33a8d69f5c3ff7e8c34a1069 Hello, there\r\n")
    client.executor(d)
