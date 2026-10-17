"""测试用临时数据库，不碰 hub/chalkback.db。必须在 import app 之前设置 HUB_DB。
测试用 mock token，所以打开联调模式（HUB_MOCK_AUTH=1）；正式模式的行为在 test_join.py 里单独测。"""
import os
import tempfile
from pathlib import Path

os.environ["HUB_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["HUB_MOCK_AUTH"] = "1"
