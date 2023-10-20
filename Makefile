.PHONY: clean testclean distclean coverageclean nuke

clean:
	-find . -name __pycache__ -print0 | xargs -0 rm -rf
	-find . -name "*.pyc" -print0 | xargs -0 rm -rf
	-find . -name "*.egg-info" -print0 | xargs -0 rm -rf

lintclean:
	-rm -rf .ruff_cache

distclean:
	-rm -rf ./dist
	-rm -rf ./build

coverageclean:
	-rm .coverage
	-rm .coverage.*
	-rm coverage.xml
	-rm -rf htmlcov
	-rm -rf reports

testclean: coverageclean clean
	-rm -rf .tox

nuke: clean distclean testclean lintclean
