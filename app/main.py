"""被测电商应用：所有 HTTP 接口都定义在这个文件里。

启动方式（必须在项目根目录下执行）：
    uvicorn app.main:app --reload
"""
import hashlib
import secrets
import sqlite3

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from app.database import get_db, init_db, reset_db, seed_products

# 导入时就确保数据库和演示数据就绪（内置了"已存在就跳过"的保护，重复运行安全）
init_db()
seed_products()

app = FastAPI(title="电商演示系统", description="个人接口测试练习用被测系统")


# ---------- 请求体模型：定义每个接口"接收什么样的 JSON" ----------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=30)


class LoginRequest(BaseModel):
    username: str
    password: str


class OrderRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int = Field(gt=0)  # gt=0：数量必须大于 0，否则 FastAPI 自动返回 422


class CartItemRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int = Field(gt=0)  # 购物车数量同样必须大于 0


class CheckoutRequest(BaseModel):
    user_id: int


def hash_password(password: str) -> str:
    """密码不存明文，存哈希值。sha256 是单向函数，无法从哈希反推出原密码。"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ---------- 接口 ----------
@app.get("/health")
def health():
    """健康检查：服务是否活着。测试脚本也用它判断服务有没有启动成功。"""
    return {"status": "ok"}


@app.post("/test/reset")
def test_reset():
    """【仅供测试】把数据库重置成初始种子状态（清空用户/订单/购物车，恢复库存）。

    这是给自动化测试"数据隔离"用的辅助接口，请配合独立的测试库使用。
    真实生产系统不应暴露此能力。
    """
    reset_db()
    return {"status": "reset"}


@app.get("/products")
def list_products():
    """商品列表：返回所有商品的当前价格和库存。"""
    conn = get_db()
    rows = conn.execute("SELECT id, name, price, stock FROM products").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/products/{product_id}")
def get_product(product_id: int):
    """商品详情：URL 路径里的数字会自动传给 product_id 参数。"""
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, price, stock FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()
    conn.close()
    if row is None:
        # 404 = 资源不存在。HTTPException 会把状态码和错误信息返回给调用方
        raise HTTPException(status_code=404, detail="商品不存在")
    return dict(row)


@app.post("/register", status_code=201)
def register(req: RegisterRequest):
    """注册：用户名唯一、密码 6~30 位。成功返回 201（Created）。"""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (req.username, hash_password(req.password)),
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        # username 有 UNIQUE 唯一约束，重复插入会触发该异常 → 409 冲突
        raise HTTPException(status_code=409, detail="用户名已存在")
    finally:
        conn.close()
    return {"id": user_id, "username": req.username}


@app.post("/login")
def login(req: LoginRequest):
    """登录：校验用户名和密码，成功返回一个随机 token。"""
    conn = get_db()
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (req.username,),
    ).fetchone()
    conn.close()
    if row is None or row["password_hash"] != hash_password(req.password):
        # 401 = 未认证。用户不存在和密码错误返回同一提示，避免泄露"用户名是否存在"
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"token": secrets.token_hex(16), "user_id": row["id"]}


# ---------- 购物车接口 ----------
@app.post("/cart/items")
def add_cart_item(req: CartItemRequest, response: Response):
    """加入购物车：商品必须存在。同一商品重复添加时数量累加。

    新添加返回 201；合并到已有条目返回 200（用 response.status_code 动态改状态码）。
    """
    conn = get_db()
    try:
        user = conn.execute("SELECT id FROM users WHERE id = ?", (req.user_id,)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")

        product = conn.execute(
            "SELECT id, name FROM products WHERE id = ?", (req.product_id,)
        ).fetchone()
        if product is None:
            raise HTTPException(status_code=404, detail="商品不存在")

        existing = conn.execute(
            "SELECT id, quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
            (req.user_id, req.product_id),
        ).fetchone()
        if existing:
            new_qty = existing["quantity"] + req.quantity
            conn.execute(
                "UPDATE cart_items SET quantity = ? WHERE id = ?",
                (new_qty, existing["id"]),
            )
            conn.commit()
            response.status_code = 200
            return {
                "cart_item_id": existing["id"],
                "product_id": req.product_id,
                "quantity": new_qty,
                "merged": True,
            }
        cur = conn.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)",
            (req.user_id, req.product_id, req.quantity),
        )
        conn.commit()
        return {
            "cart_item_id": cur.lastrowid,
            "product_id": req.product_id,
            "quantity": req.quantity,
            "merged": False,
        }
    finally:
        conn.close()


@app.get("/cart/{user_id}")
def get_cart(user_id: int):
    """查看购物车：JOIN 商品表查出名称和单价，逐条算小计，最后算总金额。"""
    conn = get_db()
    try:
        user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        rows = conn.execute(
            "SELECT c.id AS cart_item_id, c.product_id, p.name, p.price, c.quantity "
            "FROM cart_items c JOIN products p ON p.id = c.product_id "
            "WHERE c.user_id = ? ORDER BY c.id",
            (user_id,),
        ).fetchall()
        items = []
        total = 0.0
        for r in rows:
            subtotal = round(r["price"] * r["quantity"], 2)
            total = round(total + subtotal, 2)
            items.append(
                {
                    "cart_item_id": r["cart_item_id"],
                    "product_id": r["product_id"],
                    "name": r["name"],
                    "price": r["price"],
                    "quantity": r["quantity"],
                    "subtotal": subtotal,
                }
            )
        return {"user_id": user_id, "items": items, "total_price": total}
    finally:
        conn.close()


@app.patch("/cart/items")
def update_cart_item(req: CartItemRequest):
    """修改数量：把某商品在购物车里的数量直接改成新值（不是累加）。"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM cart_items WHERE user_id = ? AND product_id = ?",
            (req.user_id, req.product_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="购物车中没有该商品")
        conn.execute(
            "UPDATE cart_items SET quantity = ? WHERE id = ?", (req.quantity, row["id"])
        )
        conn.commit()
        return {"cart_item_id": row["id"], "product_id": req.product_id, "quantity": req.quantity}
    finally:
        conn.close()


@app.delete("/cart/{user_id}/items/{product_id}")
def delete_cart_item(user_id: int, product_id: int):
    """从购物车删除某个商品。成功返回 200；条目不存在返回 404。"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM cart_items WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="购物车中没有该商品")
        conn.execute("DELETE FROM cart_items WHERE id = ?", (row["id"],))
        conn.commit()
        return {"deleted": True, "user_id": user_id, "product_id": product_id}
    finally:
        conn.close()


@app.post("/cart/checkout")
def checkout_cart(req: CheckoutRequest):
    """结算购物车：每个商品各生成一张订单并扣库存，最后清空购物车。

    业务规则（整体成功或整体失败）：
    - 购物车为空 → 409
    - 任何一个商品库存不足 → 409，且整单不生效（回滚，不产生半成品数据）
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT c.product_id, c.quantity, p.name, p.price, p.stock "
            "FROM cart_items c JOIN products p ON p.id = c.product_id "
            "WHERE c.user_id = ? ORDER BY c.id",
            (req.user_id,),
        ).fetchall()
        if not rows:
            raise HTTPException(status_code=409, detail="购物车为空")

        for r in rows:
            if r["quantity"] > r["stock"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"库存不足：{r['name']} 需要 {r['quantity']}，仅剩 {r['stock']}",
                )

        orders = []
        total = 0.0
        for r in rows:
            item_total = round(r["price"] * r["quantity"], 2)
            cur = conn.execute(
                "INSERT INTO orders (user_id, product_id, quantity, total_price, status) "
                "VALUES (?, ?, ?, ?, 'created')",
                (req.user_id, r["product_id"], r["quantity"], item_total),
            )
            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (r["quantity"], r["product_id"]),
            )
            orders.append(
                {
                    "order_id": cur.lastrowid,
                    "product_id": r["product_id"],
                    "product_name": r["name"],
                    "quantity": r["quantity"],
                    "total_price": item_total,
                }
            )
            total = round(total + item_total, 2)

        conn.execute("DELETE FROM cart_items WHERE user_id = ?", (req.user_id,))
        conn.commit()
        return {"user_id": req.user_id, "orders": orders, "total_price": total}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.post("/orders", status_code=201)
def create_order(req: OrderRequest):
    """下单：校验用户/商品/库存，创建订单并扣减库存（两步一起成功或一起失败）。"""
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id FROM users WHERE id = ?", (req.user_id,)
        ).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")

        product = conn.execute(
            "SELECT id, name, price, stock FROM products WHERE id = ?",
            (req.product_id,),
        ).fetchone()
        if product is None:
            raise HTTPException(status_code=404, detail="商品不存在")
        if req.quantity > product["stock"]:
            raise HTTPException(status_code=409, detail="库存不足")

        total_price = round(product["price"] * req.quantity, 2)
        cur = conn.execute(
            "INSERT INTO orders (user_id, product_id, quantity, total_price, status) "
            "VALUES (?, ?, ?, ?, 'created')",
            (req.user_id, req.product_id, req.quantity, total_price),
        )
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (req.quantity, req.product_id),
        )
        # 插入订单和扣库存一起提交（事务），保证"要么都成功，要么都不生效"
        conn.commit()
        order_id = cur.lastrowid
    finally:
        conn.close()
    return {
        "order_id": order_id,
        "product_name": product["name"],
        "quantity": req.quantity,
        "total_price": total_price,
        "status": "created",
    }
