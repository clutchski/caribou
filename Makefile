
.PHONY: *

# test against all versions of python
check:	clean fmtcheck lint test tox


# Run all automated tests for one version of python
ci: clean fmtcheck lint test


deps:
	uv sync

tox:
	tox

test:
	python -m pytest
	./tests/test_cli.sh

clean:
	rm -rf build dist __pycache__

flake8:
	flake8 caribou tests

lint: flake8

build:
	flit build

install:
	flit install

publish: check
	flit publish

fmt:
	black caribou tests

fmtcheck:
	python -m black --check caribou tests


#
# tag
# git tag 0.4.1
# git push --tags
# 
