PY ?= python

.PHONY: help check validate-examples sync-schemas seed-mock console hub test up down reset-mock teacher school

help:
	@echo "make check            契约自检 + 全部测试"
	@echo "make validate-examples 校验 contracts/examples"
	@echo "make sync-schemas     把 contracts/*.schema.json 复制到 pipe/schemas/"
	@echo "make seed-mock        用示例数据生成 .mock-home/（假的 ~/.chalkback）"
	@echo "make console          启动控制台 :4000（使用 .mock-home）"
	@echo "make teacher          启动教师控制台 :4000 (https://localhost:4000)"
	@echo "make hub              启动 Hub :8000"
	@echo "make school           启动学校 Hub 与 Docker 服务 (https://localhost:8443)"
	@echo "make up / down        Docker：启动 / 停止 Hub + 控制台"
	@echo "make reset-mock       Docker：清空数据卷，下次 up 重新生成 mock"

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
	cd hub && $(PY) -m uvicorn app.main:app --port 8000 --reload

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
