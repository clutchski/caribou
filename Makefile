
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

lint:
	ruff check caribou tests

build:
	uv build

install:
	flit install

publish: check
	uv publish

fmt:
	ruff format caribou tests
	ruff check --fix caribou tests

fmtcheck:
	ruff format --check caribou tests

release:
ifndef VERSION
	$(error VERSION is required. Usage: make release VERSION=0.5.0)
endif
	sed -i '' 's/__version__ = ".*"/__version__ = "$(VERSION)"/' caribou/__init__.py
	git add caribou/__init__.py
	git commit -m "Bump version to $(VERSION)"
	git tag "v$(VERSION)"
	git push origin master
	git push origin "v$(VERSION)"
