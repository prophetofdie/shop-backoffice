"""
Приложение Back-office на FastAPI.
Основные возможности:
- Каталог товаров (Products)
- Клиенты (Customers)
- Заказы (Orders) со статусами и составом
- Фильтрация заказов по статусу и клиенту (по ID или части ФИО)
- Детализация заказа (join товаров для вывода артикула/названия/цены/кол-ва)
- Отчёт «Продажи по товарам» (агрегация по всем заказам)

Технические заметки:
- MongoDB клиент: motor (async)
- Обработка ObjectId -> str для ответов API
- Автодокументация: /docs (Swagger UI)
"""

import os
from datetime import datetime
from typing import List, Optional, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Загружаем переменные окружения из .env при наличии
load_dotenv()

# ---------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ ДЛЯ ObjectId
# ---------------------------------------------------------
class PyObjectId(ObjectId):
    """Класс-обёртка, чтобы Pydantic умел валидировать ObjectId как строку."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

# ---------------------------------------------------------
# Pydantic-схемы для запросов/ответов
# ---------------------------------------------------------
class ProductIn(BaseModel):
    sku: str = Field(..., description="Артикул товара")
    name: str = Field(..., description="Название товара")
    price: float = Field(..., ge=0, description="Цена за единицу")
    stock: int = Field(..., ge=0, description="Остаток на складе")

class ProductOut(ProductIn):
    id: str = Field(..., description="ID товара")

class CustomerIn(BaseModel):
    full_name: str = Field(..., description="ФИО клиента")
    email: str = Field(..., description="Email клиента")

class CustomerOut(CustomerIn):
    id: str

class OrderItemIn(BaseModel):
    product_id: str = Field(..., description="ID товара")
    quantity: int = Field(..., ge=1, description="Количество")
    unit_price: float = Field(..., ge=0, description="Цена на момент покупки")



class OrderIn(BaseModel):
    customer_id: str = Field(..., description="ID клиента")
    status: Literal["NEW", "PAID", "SHIPPED"] = Field("NEW", description="Статус заказа")
    date: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Дата заказа")
    items: List[OrderItemIn]

class OrderShortOut(BaseModel):
    id: str
    date: datetime
    status: str
    customer_id: str

class OrderItemDetailed(BaseModel):
    sku: str
    product_name: str
    unit_price: float
    quantity: int

class OrderDetailOut(BaseModel):
    id: str
    date: datetime
    status: str
    customer: CustomerOut
    items: List[OrderItemDetailed]

class SalesByProductRow(BaseModel):
    product_name: str
    total_sold_qty: int

# ---------------------------------------------------------
# ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ И БАЗЫ ДАННЫХ
# ---------------------------------------------------------
app = FastAPI(title="Shop Back-office API", version="1.0.0")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/shopdb")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.get_default_database()  # берём БД из URI (последний сегмент)

products_col = db["products"]
customers_col = db["customers"]
orders_col = db["orders"]

# Создадим полезные индексы (асинхронно при первом запросе)
@app.on_event("startup")
async def on_startup():
    # Индексы: уникальность артикулов, поиск клиентов, ускорение по заказам
    await products_col.create_index("sku", unique=True)
    await customers_col.create_index("email", unique=True)
    await customers_col.create_index("full_name")
    await orders_col.create_index("status")
    await orders_col.create_index("customer_id")
    await orders_col.create_index("date")

# ---------------------------------------------------------
# УТИЛИТЫ ПРЕОБРАЗОВАНИЯ ДОКУМЕНТОВ В СХЕМЫ ОТВЕТА
# ---------------------------------------------------------

def product_to_out(doc) -> ProductOut:
    return ProductOut(id=str(doc["_id"]), sku=doc["sku"], name=doc["name"], price=doc["price"], stock=doc["stock"])


def customer_to_out(doc) -> CustomerOut:
    return CustomerOut(id=str(doc["_id"]), full_name=doc["full_name"], email=doc["email"])


# ---------------------------------------------------------
# ЭНДПОИНТЫ: PRODUCTS
# ---------------------------------------------------------
@app.get("/products", response_model=List[ProductOut], summary="Список товаров")
async def list_products():
    # Возвращаем весь каталог товаров
    docs = await products_col.find({}).to_list(None)
    return [product_to_out(d) for d in docs]


@app.post("/products", response_model=ProductOut, summary="Создать товар")
async def create_product(body: ProductIn):
    # Вставляем товар, проверяем уникальность sku индексом
    doc = body.model_dump()
    res = await products_col.insert_one(doc)
    created = await products_col.find_one({"_id": res.inserted_id})
    return product_to_out(created)


# ---------------------------------------------------------
# ЭНДПОИНТЫ: CUSTOMERS
# ---------------------------------------------------------
@app.get("/customers", response_model=List[CustomerOut], summary="Список клиентов")
async def list_customers():
    docs = await customers_col.find({}).to_list(None)
    return [customer_to_out(d) for d in docs]


@app.post("/customers", response_model=CustomerOut, summary="Создать клиента")
async def create_customer(body: CustomerIn):
    doc = body.model_dump()
    res = await customers_col.insert_one(doc)
    created = await customers_col.find_one({"_id": res.inserted_id})
    return customer_to_out(created)



# ---------------------------------------------------------
# ЭНДПОИНТЫ: ORDERS
# ---------------------------------------------------------
@app.get("/orders", response_model=List[OrderShortOut], summary="Список заказов с фильтрами")
async def list_orders(
    status: Optional[str] = Query(None, description="Фильтр по статусу, например NEW/PAID/SHIPPED"),
    customer_id: Optional[str] = Query(None, description="Фильтр по ID клиента"),
    customer_name: Optional[str] = Query(None, description="Часть ФИО клиента для поиска"),
):
    # Строим запрос по условиям
    query = {}

    if status:
        query["status"] = status

    # Поиск по ID клиента — просто фильтр по полю
    if customer_id:
        try:
            query["customer_id"] = ObjectId(customer_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Некорректный формат customer_id")

    # Поиск по ФИО клиента (частичное совпадение, регистронезависимо)
    if customer_name:
        # Находим всех клиентов, чьё ФИО содержит искомую подстроку
        customer_docs = await customers_col.find({
            "full_name": {"$regex": customer_name, "$options": "i"}
        }, {"_id": 1}).to_list(None)
        ids = [d["_id"] for d in customer_docs]
        query["customer_id"] = {"$in": ids or [ObjectId()]}  # если список пуст, подставим нереальный id

    # Выполняем поиск заказов с сортировкой по дате (новые сверху)
    docs = await orders_col.find(query).sort("date", -1).to_list(None)
    result = [
        OrderShortOut(
            id=str(d["_id"]),
            date=d["date"],
            status=d["status"],
            customer_id=str(d["customer_id"])  # как строку
        )
        for d in docs
    ]
    return result


@app.post("/orders", response_model=OrderShortOut, summary="Создать заказ")
async def create_order(body: OrderIn):
    # Валидация существования клиента
    try:
        cust_id = ObjectId(body.customer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный customer_id")

    customer = await customers_col.find_one({"_id": cust_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Валидация элементов: наличие товаров и достаточный stock (упрощённая логика)
    for it in body.items:
        try:
            pid = ObjectId(it.product_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Некорректный product_id")
        prod = await products_col.find_one({"_id": pid})
        if not prod:
            raise HTTPException(status_code=404, detail=f"Товар {it.product_id} не найден")
        if prod["stock"] < it.quantity:
            raise HTTPException(status_code=400, detail=f"Недостаточно остатка для товара {prod['name']}")

    # Списываем остатки 
    for it in body.items:
        await products_col.update_one({"_id": ObjectId(it.product_id)}, {"$inc": {"stock": -it.quantity}})

    # Сохраняем заказ с нормализованными ObjectId
    doc = {
        "customer_id": cust_id,
        "status": body.status,
        "date": body.date or datetime.utcnow(),
        "items": [
            {
                "product_id": ObjectId(it.product_id),
                "quantity": it.quantity,
                "unit_price": it.unit_price,
            }
            for it in body.items
        ]
    }
    res = await orders_col.insert_one(doc)
    created = await orders_col.find_one({"_id": res.inserted_id})
    return OrderShortOut(
        id=str(created["_id"]),
        date=created["date"],
        status=created["status"],
        customer_id=str(created["customer_id"])
    )


@app.get("/orders/{order_id}", response_model=OrderDetailOut, summary="Детализация заказа")
async def get_order_detail(order_id: str):
    # Получаем заказ по ID
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный order_id")


    order = await orders_col.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    # Загружаем клиента
    customer = await customers_col.find_one({"_id": order["customer_id"]})
    if not customer:
        raise HTTPException(status_code=500, detail="Данные клиента повреждены")

    # Собираем детали по товарам заказа одним запросом (in)
    product_ids = list({it["product_id"] for it in order["items"]})
    prod_map = {}
    if product_ids:
        products = await products_col.find({"_id": {"$in": product_ids}}).to_list(None)
        prod_map = {p["_id"]: p for p in products}

    # Формируем список детализированных позиций
    detailed_items = []
    for it in order["items"]:
        prod = prod_map.get(it["product_id"]) or {}
        detailed_items.append(OrderItemDetailed(
            sku=prod.get("sku", "—"),
            product_name=prod.get("name", "Товар удалён"),
            unit_price=float(it["unit_price"]),
            quantity=int(it["quantity"])
        ))

    return OrderDetailOut(
        id=str(order["_id"]),
        date=order["date"],
        status=order["status"],
        customer=customer_to_out(customer),
        items=detailed_items
    )


# ---------------------------------------------------------
# ОТЧЁТ: ПРОДАЖИ ПО ТОВАРАМ
# ---------------------------------------------------------
@app.get("/reports/sales_by_product", response_model=List[SalesByProductRow], summary="Сводный отчёт: продажи по товарам")
async def report_sales_by_product():
    """Агрегируем общее количество проданных единиц по каждому товару."""
    pipeline = [
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.product_id",
            "total_sold_qty": {"$sum": "$items.quantity"}
        }},
        {"$lookup": {
            "from": "products",
            "localField": "_id",
            "foreignField": "_id",
            "as": "prod"
        }},
        {"$unwind": {"path": "$prod", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "product_name": {"$ifNull": ["$prod.name", "Товар удалён"]},
            "total_sold_qty": 1
        }},
        {"$sort": {"total_sold_qty": -1, "product_name": 1}}
    ]

    rows = await orders_col.aggregate(pipeline).to_list(None)
    return [SalesByProductRow(product_name=r["product_name"], total_sold_qty=int(r["total_sold_qty"])) for r in rows]


# ---------------------------------------------------------
# DEV: Тестовые сиды для быстрого старта 
# ---------------------------------------------------------
@app.post("/dev/seed", summary="Засеять БД тестовыми данными")
async def dev_seed():
    # Очищаем коллекции
    await products_col.delete_many({})
    await customers_col.delete_many({})
    await orders_col.delete_many({})

    # Добавим товары
    prods = [
        {"sku": "SKU-001", "name": "Кружка", "price": 9.99, "stock": 100},
        {"sku": "SKU-002", "name": "Футболка", "price": 19.9, "stock": 50},
        {"sku": "SKU-003", "name": "Рюкзак", "price": 49.0, "stock": 30},
    ]
    pres = await products_col.insert_many(prods)

    # Клиенты
    custs = [
        {"full_name": "Иван Петров", "email": "ivan@example.com"},
        {"full_name": "Мария Сидорова", "email": "maria@example.com"},
    ]
    cres = await customers_col.insert_many(custs)

    # Пара заказов
    orders = [
        {
            "customer_id": cres.inserted_ids[0],
            "status": "NEW",
            "date": datetime.utcnow(),
            "items": [
                {"product_id": pres.inserted_ids[0], "quantity": 2, "unit_price": 9.99},
                {"product_id": pres.inserted_ids[1], "quantity": 1, "unit_price": 19.9},
            ],
        },
        {
            "customer_id": cres.inserted_ids[1],
            "status": "PAID",
            "date": datetime.utcnow(),
            "items": [
                {"product_id": pres.inserted_ids[2], "quantity": 1, "unit_price": 49.0},
            ],
        },
    ]
    await orders_col.insert_many(orders)


    return {"ok": True}

