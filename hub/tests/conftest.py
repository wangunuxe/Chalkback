"""测试用临时数据库，不碰 hub/chalkback.db。必须在 import app 之前设置 HUB_DB。"""
import os
import tempfile
from pathlib import Path

os.environ["HUB_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
