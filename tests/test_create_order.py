"""订单创建的合法路径用例：对应手工用例 TC-001 / TC-003 / TC-004。

这些用例会真正"下单、扣库存"，所以必须配合数据隔离：
    - clean_db 夹具保证每条用例前后数据库都是干净的种子状态
    - fresh_user 夹具保证每次注册的用户都是全新的

运行前提：被测服务要用独立的测试库启动（避免重置掉你的手工测试数据）：
    SHOP_DB_PATH=test_shop.db uvicorn app.main:app --reload
"""
import pytest


def get_stock(api, product_id):
    """从商品列表里取出指定商品的当前库存。"""
    response = api.get("/products")
    assert response.status_code == 200
    for item in response.json():
        if item["id"] == product_id:
            return item["stock"]
    raise AssertionError(f"商品 {product_id} 不存在")


def test_create_order_deducts_stock_and_matches_total(clean_db, fresh_user, api):
    """正常下单：库存精确减少、订单金额正确（对应 TC-001 + TC-009）。"""
    # 前置：读下单前库存
    stock_before = get_stock(api, 1)

    # 操作：下单 2 个键盘
    response = api.post(
        "/orders",
        json={"user_id": fresh_user["user_id"], "product_id": 1, "quantity": 2},
    )

    # 断言一：状态码和金额
    assert response.status_code == 201, response.text
    assert response.json()["total_price"] == 199.0 * 2

    # 断言二：库存精确减少 2（相对断言，不依赖具体库存值）
    stock_after = get_stock(api, 1)
    assert stock_after == stock_before - 2, f"库存应减少 2，实际 {stock_before} -> {stock_after}"


def test_create_order_insufficient_stock_returns_409(clean_db, fresh_user, api):
    """库存不足：下单数量超过库存时返回 409，且库存不变（对应 TC-003）。"""
    stock_before = get_stock(api, 3)  # 显示器初始库存 20

    response = api.post(
        "/orders",
        json={"user_id": fresh_user["user_id"], "product_id": 3, "quantity": 99999},
    )

    assert response.status_code == 409, response.text
    assert "库存不足" in response.json()["detail"]

    # 库存没有被扣减
    stock_after = get_stock(api, 3)
    assert stock_after == stock_before


def test_create_order_product_not_found_returns_404(clean_db, fresh_user, api):
    """商品不存在：返回 404（对应 TC-004）。"""
    response = api.post(
        "/orders",
        json={"user_id": fresh_user["user_id"], "product_id": 999, "quantity": 1},
    )
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "商品不存在"


def test_order_is_persisted_in_database(clean_db, fresh_user, api, db):
    """订单落库校验（TC-009 的数据库断言部分，阶段 6 核心用例）。

    验证三件事：
    1. orders 表里真的有这条订单（不是接口"口头"成功）
    2. 数量、金额、状态、归属用户都正确
    3. 这就是"只断言 HTTP 状态码不够"的答案——
       如果接口忘了 commit，HTTP 一切正常但这里查不到数据，用例立刻失败。
    """
    # 操作：下单 2 个机械键盘
    response = api.post(
        "/orders",
        json={"user_id": fresh_user["user_id"], "product_id": 1, "quantity": 2},
    )
    assert response.status_code == 201, response.text
    order_id = response.json()["order_id"]

    # 用 SQL 查数据库：这条订单真的存在吗？
    rows = db("SELECT * FROM orders WHERE id = ?", (order_id,))

    # 断言：恰好一条记录，且每个字段都正确
    assert len(rows) == 1, f"订单 {order_id} 应在 orders 表中有且仅有 1 条，实际 {len(rows)} 条"
    order = rows[0]
    assert order["user_id"] == fresh_user["user_id"]
    assert order["product_id"] == 1
    assert order["quantity"] == 2
    assert order["total_price"] == 398.0
    assert order["status"] == "created"


def test_stock_is_updated_in_database(clean_db, fresh_user, api, db):
    """库存落库校验：下单后，products 表里的库存真的减少了。

    clean_db 保证每条用例开始时库存都是种子值 50，所以这里可以写绝对值断言。
    """
    response = api.post(
        "/orders",
        json={"user_id": fresh_user["user_id"], "product_id": 1, "quantity": 3},
    )
    assert response.status_code == 201, response.text

    rows = db("SELECT stock FROM products WHERE id = ?", (1,))
    assert rows[0]["stock"] == 50 - 3, "下单 3 个后，数据库里键盘库存应为 50-3=47"
