"""数据库校验助手：让测试直接连数据库做断言。

为什么需要它（阶段 6 的核心思想）：
    HTTP 状态码只能证明"接口**说**它成功了"，
    查数据库才能证明"数据**真的**变了"。
    想象一个有 bug 的版本：下单接口返回 201，但忘了执行 commit——
    HTTP 一切正常，数据却没落库。只有查库的断言能抓住这种 bug。

只读原则：
    这里只提供 query()（SELECT）。测试代码不要直接 UPDATE/DELETE 业务表——
    需要重置数据时走 /test/reset 接口，责任边界清晰。
"""
import os
import sqlite3
from pathlib import Path

# 默认指向项目根目录的 shop.db；
# 和被测系统一样支持 SHOP_DB_PATH 环境变量——
# 跑测试时服务用哪个库，测试进程就要指向同一个库！
_DEFAULT_DB = Path(__file__).resolve().parent.parent / "shop.db"
DB_PATH = Path(os.environ.get("SHOP_DB_PATH", str(_DEFAULT_DB)))


def query(sql: str, params=()) -> list[dict]:
    """执行一条只读查询，返回所有行，每行是一个字典（列名 -> 值）。

    用法示例：
        rows = query("SELECT * FROM orders WHERE user_id = ?", (1,))
        rows[0]["total_price"]

    params 用 ? 占位符传参（和被测系统同款写法），防止 SQL 注入。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
