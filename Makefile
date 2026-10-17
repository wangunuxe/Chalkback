PY ?= python

.PHONY: help check validate-examples sync-schemas seed-mock mock mock-local console hub test up down reset reset-mock teacher school

help:
	@echo "make check            contract self-check + all tests"
	@echo "make validate-examples validate contracts/examples"
	@echo "make sync-schemas     copy contracts/*.schema.json to pipe/schemas/"
	@echo "make seed-mock        generate .mock-home/ from the sample data (a fake ~/.chalkback)"
	@echo "make console          start the console on :4000 (uses .mock-home; empty until make mock-local)"
	@echo "make teacher          start the teacher console on :4000 (https://localhost:4000)"
	@echo "make hub              start the Hub at https://localhost:8000 (test mode: mock token + DEMO-* invite codes)"
	@echo "make school           start the school Hub with Docker services (https://localhost:8443)"
	@echo "make up / down        Docker: start / stop Hub + console (they start with no demo data)"
	@echo "make mock             Docker: load the demo data into the running Hub + console (run make up first)"
	@echo "make mock-local       same for make hub + make teacher (Hub https://localhost:8000, .mock-home)"
	@echo "make reset            Docker: stop and wipe all data (the volumes); the next up starts empty"

up:
	docker compose up --build -d

down:
	docker compose down

reset:
	docker compose down -v

reset-mock: reset  # old name

# Demo data only exists if you ask for it. The scripts run inside the containers, so nothing needs installing on this computer.
# Safe to run again: the Hub keeps what it has and adds what is missing; the console's data is replaced by the mock.
mock:
	@for s in hub console; do docker compose ps --status running --services 2>/dev/null | grep -qx $$s \
	  || { echo "The $$s container is not running: start the servers with 'make up' first."; exit 1; }; done
	docker compose exec -T hub python scripts/seed_demo.py https://127.0.0.1:8000
	docker compose exec -T console python /app/tools/seed_mock_home.py --home /data --hub-url https://hub:8000
	@echo "Demo data loaded: Hub https://localhost:8443, console https://localhost:4000/console"

mock-local:
	$(PY) hub/scripts/seed_demo.py https://localhost:8000
	$(PY) tools/seed_mock_home.py --hub-url https://localhost:8000

validate-examples:
	$(PY) pipe/scripts/validate.py --examples

sync-schemas:
	cp contracts/*.schema.json pipe/schemas/

seed-mock:
	$(PY) tools/seed_mock_home.py

console:
	cd console && $(PY) generate_cert.py && CHALKBACK_HOME=../.mock-home $(PY) -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --reload --ssl-keyfile key.pem --ssl-certfile cert.pem

hub:
	set -a; [ -f .env ] && . ./.env; set +a; \
	cd hub && $(PY) generate_cert.py && HUB_MOCK_AUTH=1 $(PY) -m uvicorn app.main:app --port 8000 --reload --ssl-keyfile key.pem --ssl-certfile cert.pem

test:
	$(PY) -m pytest -q tests
	cd pipe && $(PY) -m pytest -q
	cd console && $(PY) -m pytest -q
	cd hub && $(PY) -m pytest -q

check: validate-examples test

teacher:
	cd console && $(PY) generate_cert.py && CHALKBACK_HOME=../.mock-home $(PY) -m uvicorn app.main:app --host 127.0.0.1 --port 4000 --reload --ssl-keyfile key.pem --ssl-certfile cert.pem

school:
	@echo "Starting School Hub & Console via Docker Compose..."
	docker compose up --build -d
	@echo "Hub is running at https://localhost:8443"
	@echo "Console is running at https://localhost:4000"
