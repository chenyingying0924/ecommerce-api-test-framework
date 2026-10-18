"""数据库模块：负责 SQLite 连接、建表、演示数据和测试重置。

SQLite 是一个"文件数据库"：整个数据库就是项目目录下的一个文件（shop.db），
不需要安装任何数据库软件，最适合个人练习。

测试环境隔离：
    数据库文件路径可以通过环境变量 SHOP_DB_PATH 指定。
    平时手工测试用默认的 shop.db；跑自动化测试时用 SHOP_DB_PATH=test_shop.db
    启动一个独立的库，两者数据互不干扰。
"""
import os
import sqlite3
from pathlib import Path

# 数据库文件位置：默认项目根目录下的 shop.db，可用环境变量覆盖
_DEFAULT_DB = Path(__file__).resolve().parent.parent / "shop.db"
DB_PATH = Path(os.environ.get("SHOP_DB_PATH", str(_DEFAULT_DB)))

# 演示商品（种子数据）：(名称, 单价, 初始库存)
PRODUCTS = [
    ("机械键盘", 199.0, 50),
    ("无线鼠标", 89.0, 100),
    ("显示器", 899.0, 20),
]


def get_db():
    """获取一个数据库连接。

    row_factory = sqlite3.Row 的作用：让查询结果可以用列名取值，
    比如 row["name"]，而不是只能用下标 row[1]，代码更好读。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """建表。IF NOT EXISTS 表示表已存在就跳过，重复运行不会报错。"""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            UNIQUE(user_id, product_id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'created',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        """
    )
    conn.commit()
    conn.close()


def seed_products():
    """插入演示商品。只在商品表为空时插入，避免重复运行时数据翻倍。"""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", PRODUCTS
        )
        conn.commit()
    conn.close()


def reset_db():
    """把数据库重置成"刚初始化"的状态：清空用户/订单/购物车，商品库存恢复演示值。

    【重要】这是为自动化测试提供的能力，通过 /test/reset 接口调用。
    真实生产系统绝不会暴露"一键清库"的接口——本项目是个人教学项目，
    且配合独立的测试库使用，所以是安全的、合理的。

    为什么"清空商品"而是"保留商品、只恢复库存"：
        如果删掉商品再重建，SQLite 的自增 id 不会归零，重建后商品 id 会变成 4、5、6……
        测试里写死的 product_id=1 就会失效。保留商品、只回填库存，id 永远稳定。
    """
    conn = get_db()
    conn.executescript(
        """
        DELETE FROM orders;
        DELETE FROM cart_items;
        DELETE FROM users;
        """
    )
    # 按名称把每件商品的库存恢复成演示值（不依赖 id，更稳）
    for name, _price, stock in PRODUCTS:
        conn.execute("UPDATE products SET stock = ? WHERE name = ?", (stock, name))
    conn.commit()
    conn.close()
