"""第一条接口自动化测试：健康检查接口。

运行方式（在项目根目录、已激活 .venv、被测服务已启动的前提下）：
    pytest tests/test_health.py -v

这个文件演示了接口自动化测试的最小骨架：
    通过 api 夹具发真实 HTTP 请求 → 用 assert 断言响应是否符合预期
"""


def test_health_should_return_ok(api):
    """验证 /health 返回 200，且响应体里 status 字段为 ok。

    注意函数参数里的 api：它就是 tests/conftest.py 里定义的 fixture，
    pytest 看到这个名字会自动把 ApiClient 实例传进来。
    """

    # 1) 发送 GET 请求。api.get 返回一个"响应对象"（Response），
    #    它把状态码、响应头、响应体都打包在一起
    response = api.get("/health")

    # 2) 断言一：状态码。assert 后面的条件为 False 时，pytest 会把这条用例判为失败，
    #    并把逗号后面的文字作为失败原因显示出来
    assert response.status_code == 200, f"预期 200，实际 {response.status_code}，响应体：{response.text}"

    # 3) 断言二：响应字段。response.json() 把 JSON 文本解析成 Python 字典，
    #    然后像查字典一样取出 status 字段和预期值比较
    body = response.json()
    assert body["status"] == "ok", f"预期 status=ok，实际响应体：{body}"
