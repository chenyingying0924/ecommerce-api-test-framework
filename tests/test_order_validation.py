"""用参数化把手工用例 TC-006 / 007 / 008 翻译成自动化代码。

运行（项目根目录、已激活 .venv、被测服务已启动）：
    pytest tests/test_order_validation.py -v

为什么这里只测"非法数量"：
    非法请求在进业务逻辑之前就被 422 拦截，不会写数据库（无副作用），
    所以这批用例可以反复运行、结果稳定。
    合法下单会扣库存、污染数据，等数据隔离机制就绪后再补。
"""
import pytest


@pytest.mark.parametrize(
    # ↓ 这一行按顺序声明每组数据的三个"槽位"：描述、数量、预期状态码
    "desc, quantity, expected_code",
    [
        # ↓ 每个元组就是一组数据，pytest 会为每组各生成一条用例
        ("数量为0-下边界外", 0, 422),     # 对应手工用例 TC-ORDER-006
        ("数量为负数", -1, 422),          # 对应手工用例 TC-ORDER-007
        ("数量为小数", 2.5, 422),         # 对应手工用例 TC-ORDER-008
        ("数量为字符串", "abc", 422),     # 非法类型的另一种代表值
    ],
)
def test_order_quantity_invalid(api, desc, quantity, expected_code):
    """同一套测试逻辑，喂 4 组不同数据，pytest 自动执行 4 遍。

    参数里同时有 api（fixture 注入）和 desc/quantity/expected_code（参数化注入），
    两种机制可以混用。
    """

    # 注意和上一版的两点变化：
    # 1) 不再自己拼 URL——api 客户端知道服务地址，只传路径 /orders
    # 2) json= 参数会自动把字典转成 JSON，并自动加 Content-Type: application/json
    response = api.post("/orders", json={"user_id": 1, "product_id": 1, "quantity": quantity})

    # 断言状态码等于该组数据预期的值
    assert response.status_code == expected_code, (
        f"[{desc}] 预期 {expected_code}，实际 {response.status_code}，响应：{response.text}"
    )
