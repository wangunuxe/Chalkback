PY ?= python

.PHONY: help check validate-examples sync-schemas seed-mock console hub test up down reset-mock teacher school

help:
	@echo "make check            contract self-check + all tests"
	@echo "make validate-examples validate contracts/examples"
	@echo "make sync-schemas     copy contracts/*.schema.json to pipe/schemas/"
	@echo "make seed-mock        generate .mock-home/ from the sample data (a fake ~/.chalkback)"
	@echo "make console          start the console on :4000 (uses .mock-home)"
	@echo "make teacher          start the teacher console on :4000 (https://localhost:4000)"
	@echo "make hub              start the Hub at https://localhost:8000 (test mode: mock token + DEMO-* invite codes)"
	@echo "make school           start the school Hub with Docker services (https://localhost:8443)"
	@echo "make up / down        Docker: start / stop Hub + console"
	@echo "make reset-mock       Docker: wipe the data volumes; the next up regenerates the mock"

up:
	docker compose up --build -d

down:
	docker compose down

reset-mock:
	docker compose down -v

validate-examples:
	$(PY) pipe/scripts/validate.py --examples

sync-schemas:
	cp contracts/*.schema.json pipe/schemas/

seed-mock:
	$(PY) tools/seed_mock_home.py

console: seed-mock
	cd console && $(PY) generate_cert.py && CHALKBACK_HOME=../.mock-home $(PY) -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --reload --ssl-keyfile key.pem --ssl-certfile cert.pem

hub:
	cd hub && $(PY) generate_cert.py && HUB_MOCK_AUTH=1 $(PY) -m uvicorn app.main:app --port 8000 --reload --ssl-keyfile key.pem --ssl-certfile cert.pem

test:
	$(PY) -m pytest -q tests
	cd pipe && $(PY) -m pytest -q
	cd console && $(PY) -m pytest -q
	cd hub && $(PY) -m pytest -q

check: validate-examples test

teacher: seed-mock
	cd console && $(PY) generate_cert.py && CHALKBACK_HOME=../.mock-home $(PY) -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --reload --ssl-keyfile key.pem --ssl-certfile cert.pem

school:
	@echo "Starting School Hub & Console via Docker Compose..."
	docker compose up --build -d
	@echo "Hub is running at https://localhost:8443"
	@echo "Console is running at https://localhost:4000"
