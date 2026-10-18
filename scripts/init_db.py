"""命令行脚本：手动初始化数据库并准备演示数据。

用法（在项目根目录、已激活虚拟环境时执行）：
    python scripts/init_db.py
"""
import sys
from pathlib import Path

# 把项目根目录加入模块搜索路径，这样脚本才能 import app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import DB_PATH, init_db, seed_products

if __name__ == "__main__":
    init_db()
    seed_products()
    print(f"数据库初始化完成：{DB_PATH}")
    print("已内置演示商品：机械键盘 / 无线鼠标 / 显示器")
