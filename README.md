# 基于 Python + Pytest 的电商系统接口自动化测试框架

> E-commerce API Test Automation Framework Based on Python and Pytest

一个从零搭建的**个人接口自动化测试练习项目**：先用 FastAPI 自研一个电商被测系统，再围绕它设计测试用例、编写 pytest 自动化测试、做数据库校验、生成 Allure 报告，最后用 Git 管理、通过 GitHub Actions 持续集成。

> **诚实声明**：这是个人练习项目，被测系统与测试框架均由本人（在 AI 辅助下）完成，不涉及任何企业项目或真实商业系统。

## 项目目标

证明并练习以下软件测试初级能力：

- 理解测试基本流程：需求 → 用例设计 → 执行 → 缺陷记录 → 报告
- 使用等价类划分 / 边界值分析 / 状态迁移设计测试用例
- 使用 requests + pytest 编写接口自动化测试
- 用 SQL 校验业务数据（接口返回成功 ≠ 数据正确）
- 通过故障注入验证测试有效性
- 组织测试代码、配置、数据与报告

## 技术栈

| 分类 | 技术 |
|------|------|
| 被测系统 | Python · FastAPI · SQLite |
| 测试框架 | pytest · requests · 参数化 · fixture · allure-pytest |
| 报告 | Allure |
| 工程化 | Git · requirements.txt · GitHub Actions CI |

## 项目结构

```
├── app/                    # 被测系统（电商服务）
│   ├── main.py             # 11 个 HTTP 接口
│   └── database.py         # SQLite 建表、种子数据、测试重置
├── common/                 # 测试框架支撑
│   ├── config.py           # 配置（BASE_URL / TIMEOUT，支持环境变量覆盖）
│   ├── api_client.py       # API 封装层（统一发请求）
│   └── db.py               # 数据库校验助手（只读查询）
├── tests/                  # 测试用例
│   ├── conftest.py         # fixture：api / clean_db / fresh_user / db
│   ├── test_health.py      # 健康检查
│   ├── test_order_validation.py   # 参数化：非法数量 → 422
│   └── test_create_order.py       # 下单 + 数据库断言
├── docs/                   # 文档
│   ├── 业务规则说明.md
│   ├── 测试用例设计.md
│   └── 缺陷记录.md
├── scripts/init_db.py      # 手动初始化数据库
├── .github/workflows/ci.yml # CI 自动执行测试
├── pytest.ini              # pytest 配置（中文用例名等）
├── requirements.txt
└── .gitignore
```

## 环境要求

- Python 3.10+
- macOS / Linux / Windows 均可
- （可选）Java 8+ 与 Allure 命令行，用于生成网页报告

## 安装与启动

```bash
# 1) 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2) 安装依赖
pip install -r requirements.txt

# 3) 启动被测服务（默认 http://127.0.0.1:8000，自带交互式文档 /docs）
uvicorn app.main:app --reload
```

## 如何运行测试

**重要：自动化测试要使用独立的测试数据库**（避免重置你的手工测试数据）。

```bash
# 终端 1：用独立测试库启动服务
SHOP_DB_PATH=test_shop.db uvicorn app.main:app --reload

# 终端 2：运行测试（pytest 进程也要指向同一个库）
SHOP_DB_PATH=test_shop.db pytest tests/ -v
```

预期输出：`10 passed`。

## 测试覆盖范围

| 模块 | 接口 | 覆盖点 |
|------|------|--------|
| 健康检查 | GET /health | 服务存活 |
| 订单创建 | POST /orders | 正常下单、库存精确扣减、库存不足 409、商品/用户不存在 404、非法数量 422（0/负数/小数/字符串） |
| 数据一致性 | orders / products 表 | 订单落库、金额正确、库存落库（直接查库断言） |

另见 `docs/测试用例设计.md`（10 条手工用例）与 `docs/缺陷记录.md`（故障注入实验）。

## 测试报告

```bash
# 生成 Allure 结果数据并预览
SHOP_DB_PATH=test_shop.db pytest tests/ -v --alluredir=allure-results --clean-alluredir
allure serve allure-results

# 生成静态 HTML 报告（可发给他人）
allure generate allure-results -o allure-report --clean
```

## 数据库校验说明

接口返回 `200/201` 只代表“接口说它成功了”，**不证明数据真的变了**。本项目用 `common/db.py` 直接查询 SQLite，断言订单真的落库、库存真的扣减——通过故障注入实验（故意删除 `commit()`）验证了这些数据库断言能抓住“接口说谎”类缺陷（详见 `docs/缺陷记录.md` 的 BUG-001）。

## 已知问题与限制

- 登录返回 token，但接口未强制校验 token（越权风险，真实系统必须修复）
- 下单接口不具备幂等性（重复请求会产生多张订单）
- `/test/reset` 测试专用重置接口仅存在于本项目，真实生产环境不应暴露

## 已完成 / 未完成

**已完成**：被测系统（注册/登录/商品/购物车/订单）、10 条手工用例、10 条自动化用例、fixture 数据隔离、数据库校验、故障注入实验、Allure 报告、Git 管理、CI。

**未完成**：购物车结算的自动化用例、订单状态流转、token 鉴权、幂等控制。
