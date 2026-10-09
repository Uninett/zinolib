=========
CHANGELOG
=========

1.3.5 2026-10-09
================

Added
-----

* Test on Python 3.12 on Github
* This changelog

Changed
-------

* Update dependencies of CI on Github
* Upgrade linters and pre-commit itself

1.3.4 2025-07-24
================

"howitz" was officially mothballed on 2025-10-07, "zino-argus-glue" started
using zinolib 2025-03-17.

Fixed
-----

* Fix history parsing logic

Added
-----

* Support TCP keepalive on NetBSD

Changed
-------

* Upgrade linters in pre-commit and ensure Github uses the same versions and
  methods in CI
* Fix markup in README

0.10.1 2025-07-24
=================

Hopefully the last release on the 0-branch.

Fixed
-----

* Fix history parsing logic

Added
-----

* Support TCP keepalive on NetBSD

Changed
-------

* Switch from black to ruff to lint and reformat, and reformat once again

1.3.3 2024-07-04
================

Changed
-------

* Close connections in an even more paranoid fashion to ensure cleanup

1.3.2 2024-07-04
================

Changed
-------

* Raise NotConnectedError instead of AttributeError if the session object has
  been garbled when checking connection

1.3.1 2024-07-03
================

Changed
-------

* Improve _verify_session:
  * no longer raising an exception on disconnect
  * Raise NotConnectedError instead of ValueError if the connection is gone

1.3.0 2024-06-24
================

Added
-----

* Support for TCP keepalive, on by default

Changed
-------

* Rework coverage reports on Github in CI

0.10.0 2024-06-24
=================

Added
-----

* Support for TCP keepalive, on by default

1.2.0 2024-06-11
================

Added
-----

* New method "is_down" on CVase, varying by Case-type to make it easier to check
  if there is a down-event
* New way to test if the connection to the server is up, ask for a non-existent
  event

Changed
-------

* Stop renaming NotConnectedError, LostconnectionError, to catch them easier

1.1.1 2024-06-06
================

Changed
-------

* Raise better errors for lost connection

1.1.0 2024-05-31
================

Fixed
-----

* Fix bug in config factories, important for tests
* Fix bug when reconnecting to the push channel

Changed
-------

* Improve docstring for the new way of doing things

1.0.4 2024-05-24
================

Added
-----

* Handle "unknown" AdmState

Changed
-------

* Raise socket error when there's trouble with the update channel

0.9.23 2024-04-12
=================

Bugfix-release

Fixed
-----

* Fix a typoed variable name
* Revert to the old and risky way to set attributes on Case because fixing
  curitz to work with the safer way was too much work

Changed
-------

* Improve the traceback for when a Case misses an attribute now that we get
  them in an unsafe fashion again.

1.0.3 2024-04-02
================

Fixed
-----

* Handle broken connections better when sending to server

Added
-----

* Add support for triggering a server poll for an event

Changed
-------

* Improve clear_flapping(), the input can now be either an event id or an
  already fetched event

1.0.2 2024-01-26
================

Fixed
-----

* Fix an error when parsing broken log records
* Fix an error when parsing invalid event ids

Changed
-------

* Alter CI setup in Github, lint moar

1.0.1 2024-01-11
================

Added
-----

* Support Python 3.12
* Add a RetryError to help clients on flaky connections
* Add a place to store misc case data

Changed
-------

* Improve logging of wire protocol errors
* Replace "unknown" bfd_addr with None

1.0.0 2023-10-26
================

First release for zinolib as a more standalone library, split branches for
curitz and using zinolib as a library.

The big new thing is an OO way of handling cases, which uses enums for states.
It decouples a case from the wire protocol in anticipation of supporting
a different type of API. This also saw the start of "howitz", a web client to
zino depending on the 1-branch instead of the 0-branch.

Fixed
-----

* Fix a typoed variable name

Added
-----

* Add an Object Oriented way to model Cases with the help of Pydantic
* Lots of type hints in the new code
* Configuration can be done via TOML-file

Removed
-------

* Drop support for Pythons older than 3.9

Changed
-------

* Revert to the old and risky way to set attributes on Case because fixing
  curitz to work with the safer way was too much work
* Refactor how config parsing happens in anticipation of supporting TOML.
* Move slow tests to a separate file to make it easy to exclude when rerunning
  tests
* Always store port numbers as int
* Switch test runner from unittest to pytest
* Have the oldest bits use ZinoError in many places instead of ProtocolError
  and Exception, for easier catching of errors.

0.9.22 2023-08-23
=================

Bugfix-release, split branches for curitz and using zinolib as a library.

Fixed
-----

* Add a class constant that was missed during the refactor in 0.9.21, now
  preventing a crash.

Changed
-------

* Refactor getting logs and history so that the API fetch and decoding is two
  separate methods. Makes for easier testing and extension.


0.9.21 2023-08-15
=================

Added
-----

* Set up Github CI, with automatic linting
* Use Codecov for coverage

Fixed
-----

* Switch from supporting windows codepage 1251 (cyrrillic) to windows
  codepage 1252i (a superset of ISO-8859-1), necessary to better
  support UTF-8.
* Improve readability of some tests
* Control timezone better when testing, fixing some intermittently failing tests

Changed
-------

* Reformat code as per PEP8 and set up code reformatting tools and procedures
* Set attributes on Case in a less risky/more easily testable manner than before
* Refactor and clean up the code
* Standardize on a way to raise exceptions, DRYing the code a bit

0.9.20 2023-03-24
=================

Internal repo pyritz split into repos curitz and zinolib. No new features, no
bug fixes.

Added
-----

* Test with tox
* Test on Python 3.6 or newer
* Add precommit hooks for linting and syntax error checks
* Add Makefile for repo cleanup chores

Changed
-------

* Remove all things curses-relevant
* Rename project from ritz to zinolib
* Drop support for Pythons older than 3.6
* Rename function ``parse_config()`` to ``parse_tcl_config()`` in preparation
  for supporting other config formats, and improve documentation.
* Move source to src/ and get version number from git tag
* Switch from setup.py to pyproject.toml for package-building
* License as Apache-2.0
