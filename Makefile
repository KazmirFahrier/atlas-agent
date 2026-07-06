.PHONY: install seed run eval lint docker

install:
	pip install -e ".[dev]"

seed:
	python data/seed.py

run:
	python -m orchestrator.agent "$(Q)"

test:
	pytest -q

eval:
	python -m eval.run

lint:
	ruff check .

docker:
	docker build -t atlas-agent .
