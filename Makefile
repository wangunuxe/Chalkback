PY ?= python3

.PHONY: help check validate-examples sync-schemas seed-mock console hub test

help:
	@echo "make check            契约自检 + 全部测试"
	@echo "make validate-examples 校验 contracts/examples"
	@echo "make sync-schemas     把 contracts/*.schema.json 复制到 pipe/schemas/"
	@echo "make seed-mock        用示例数据生成 .mock-home/（假的 ~/.chalkback）"
	@echo "make console          启动控制台 :4000（使用 .mock-home）"
	@echo "make hub              启动 Hub :8000"

validate-examples:
	$(PY) pipe/scripts/validate.py --examples

sync-schemas:
	cp contracts/*.schema.json pipe/schemas/

seed-mock:
	$(PY) tools/seed_mock_home.py

console: seed-mock
	cd console && CHALKBACK_HOME=../.mock-home $(PY) -m uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload

hub:
	cd hub && $(PY) -m uvicorn app.main:app --port 8000 --reload

test:
	$(PY) -m pytest -q tests
	cd console && $(PY) -m pytest -q
	cd hub && $(PY) -m pytest -q

check: validate-examples test
