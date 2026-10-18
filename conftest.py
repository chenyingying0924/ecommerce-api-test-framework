# 项目根 conftest.py：pytest 启动时会自动加载它。
# 它的作用只有一个：把项目根目录加入模块搜索路径，
# 这样测试文件里才能 import common/ 这个包。
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
