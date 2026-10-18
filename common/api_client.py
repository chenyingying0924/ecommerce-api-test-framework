"""API 封装层：所有 HTTP 请求统一从这里发出去。

为什么要有这一层（面试可讲的三点）：
1. 超时、请求头等公共设置只写一次，不用每条用例重复；
2. 以后要加日志、加 token 认证，只改这一个文件，所有用例自动生效；
3. 测试用例里只剩下"业务动作 + 断言"，可读性大幅提高。
"""
import requests


class ApiClient:
    """一个极简的 HTTP 客户端：知道服务地址，会发四种请求。"""

    def __init__(self, base_url: str, timeout: int = 5):
        # rstrip("/") 防止 base_url 末尾多写一个斜杠导致 URL 变成 //products
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, **kwargs):
        """发送请求并返回响应对象。method 用大写：GET / POST / PATCH / DELETE。"""
        kwargs.setdefault("timeout", self.timeout)
        return requests.request(method, self.base_url + path, **kwargs)

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)
