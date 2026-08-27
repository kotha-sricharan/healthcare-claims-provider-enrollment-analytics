.PHONY: setup run test verify

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt

run:
	python3 -m src.run_pipeline

test:
	python3 -m unittest discover -s tests -v

verify: run test
