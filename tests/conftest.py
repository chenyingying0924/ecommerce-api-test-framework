"""pytest 的"共享配置"文件：同目录下的测试会自动加载这里定义的 fixture。

fixture（夹具）= 给测试用例提供的"预制材料"，可以带"前置/后置"两段动作。
测试函数只要把 fixture 的名字写成参数，pytest 就会自动把值传进来——这叫"依赖注入"。
"""
import pytest

from common.config import BASE_URL
from common.api_client import ApiClient
from common.db import query as db_query


@pytest.fixture
def api():
    """提供 API 客户端实例。"""
    return ApiClient(BASE_URL)


@pytest.fixture
def clean_db(api):
    """数据隔离的核心夹具：yield 把夹具分成"前置"和"后置"两段。

    yield 之前 = 前置（setup）：把数据库重置成干净的种子状态
    yield 之后 = 后置（teardown）：测试结束后再重置一次，不留脏数据

    只要用例把 clean_db 写进参数，就能保证"跑之前是干净的、跑之后也是干净的"，
    用例之间互不污染，可以反复运行、可以乱序运行。
    """
    api.post("/test/reset")   # 前置：重置
    yield                      # 测试体在这里执行
    api.post("/test/reset")   # 后置：再重置


@pytest.fixture
def fresh_user(api):
    """注册一个"每次都不一样"的用户，保证用户名永不会重复。

    用户名用时间戳+随机数拼接，所以即使数据库没重置、重复跑无数次，
    也不会撞上"用户名已存在"的 409。
    """
    import uuid
    username = "test_" + uuid.uuid4().hex[:8]
    response = api.post("/register", json={"username": username, "password": "test123"})
    assert response.status_code == 201, f"注册失败：{response.status_code} {response.text}"
    return {"username": username, "user_id": response.json()["id"]}


@pytest.fixture
def db():
    """提供数据库查询函数（只读）。

    用法：rows = db("SELECT * FROM orders WHERE id = ?", (order_id,))
    注意：测试进程和服务进程必须指向同一个库——
    跑测试时用 SHOP_DB_PATH=test_shop.db pytest tests/ -v，
    和启动服务时的 SHOP_DB_PATH 保持一致。
    """
    return db_query
