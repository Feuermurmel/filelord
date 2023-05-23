.PHONY: venv
venv:
	python3 -m venv --clear venv
	venv/bin/pip install --upgrade pip setuptools
	venv/bin/pip install --editable '.[dev]'

.PHONY: pytest
pytest:
	venv/bin/pytest
