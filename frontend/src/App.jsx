import React, { useEffect, useMemo, useState } from "react";
import { API_BASE, getJSON } from "./api";

// Вспомогательная функция форматирования дат
function fmtDate(s) { return new Date(s).toLocaleString(); }

export default function App() {
  // Табы интерфейса
  const [tab, setTab] = useState("orders");

  return (
    <div className="container">
      <div className="h1">Back‑office административная панель</div>

      <div className="tabs">
        <button className={`tab ${tab === 'orders' ? 'active' : ''}`} onClick={() => setTab("orders")}>Заказы</button>
        <button className={`tab ${tab === 'products' ? 'active' : ''}`} onClick={() => setTab("products")}>Товары</button>
        <button className={`tab ${tab === 'report' ? 'active' : ''}`} onClick={() => setTab("report")}>Отчёт: Продажи</button>
      </div>

      {tab === "orders" && <OrdersPage />}
      {tab === "products" && <ProductsPage />}
      {tab === "report" && <SalesReportPage />}

      <div className="small">API: {API_BASE}</div>
    </div>
  );
}

function ProductsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Загружаем каталог
  useEffect(() => {
    setLoading(true);
    getJSON("/products")
      .then(setRows)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="card">
      <div className="row"><b>Каталог товаров</b></div>
      {loading && <div>Загрузка…</div>}
      {error && <div style={{color: 'crimson'}}>{error}</div>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Артикул</th>
            <th>Название</th>
            <th>Цена</th>
            <th>Остаток</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id}>
              <td>{r.id}</td>
              <td>{r.sku}</td>
              <td>{r.name}</td>
              <td>{r.price.toFixed(2)}</td>
              <td>{r.stock}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OrdersPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Фильтры
  const [status, setStatus] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [customerName, setCustomerName] = useState("");

  // Выбранный заказ для детализации
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);

  // Функция загрузки списка заказов с учётом фильтров
  async function loadOrders() {
    setLoading(true); setError(""); setSelectedId(null); setDetail(null);
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (customerId) params.set("customer_id", customerId);
    if (customerName) params.set("customer_name", customerName);
    const qs = params.toString();
    const path = qs ? `/orders?${qs}` : "/orders";
    try {
      const data = await getJSON(path);
      setRows(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  // Первичная загрузка
  useEffect(() => { loadOrders(); }, []);

  // Когда выбираем заказ — грузим детализацию
  useEffect(() => {
    if (!selectedId) return;
    setDetail(null);
    getJSON(`/orders/${selectedId}`).then(setDetail).catch(e => setError(String(e)));
  }, [selectedId]);

  return (
    <div className="card">
      <div className="row">
        <b>Список всех заказов</b>
      </div>


      <div className="row">
        <select value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">Статус: любой</option>
          <option value="NEW">NEW</option>
          <option value="PAID">PAID</option>
          <option value="SHIPPED">SHIPPED</option>
        </select>
        <input placeholder="ID клиента" value={customerId} onChange={e => setCustomerId(e.target.value)} />
        <input placeholder="ФИО клиента (поиск по подстроке)" value={customerName} onChange={e => setCustomerName(e.target.value)} />
        <button className="tab" onClick={loadOrders}>Применить фильтры</button>
      </div>

      {loading && <div>Загрузка…</div>}
      {error && <div style={{color: 'crimson'}}>{error}</div>}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Дата</th>
            <th>Статус</th>
            <th>КлиентID</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id} onClick={() => setSelectedId(r.id)} style={{cursor: 'pointer'}}>
              <td>{r.id}</td>
              <td>{fmtDate(r.date)}</td>
              <td>{r.status}</td>
              <td>{r.customer_id}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Детализация выбранного заказа */}
      {selectedId && (
        <div className="details">
          <b>Детализация заказа</b>
          {!detail && <div>Загрузка детализации…</div>}
          {detail && (
            <div className="card" style={{marginTop: 8}}>
              <div className="row">
                <div><b>Номер:</b> {detail.id}</div>
                <div><b>Дата:</b> {fmtDate(detail.date)}</div>
                <div><b>Статус:</b> {detail.status}</div>
              </div>
              <div className="row">
                <div><b>Клиент:</b> {detail.customer.full_name}</div>
                <div className="small">{detail.customer.email}</div>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Артикул</th>
                    <th>Название товара</th>
                    <th>Цена за ед.</th>
                    <th>Кол-во</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.items.map((it, idx) => (
                    <tr key={idx}>
                      <td>{it.sku}</td>
                      <td>{it.product_name}</td>
                      <td>{it.unit_price.toFixed(2)}</td>
                      <td>{it.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SalesReportPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    getJSON("/reports/sales_by_product")
      .then(setRows)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const totalQty = useMemo(() => rows.reduce((acc, r) => acc + r.total_sold_qty, 0), [rows]);

  return (
    <div className="card">
      <div className="row"><b>Сводный отчёт: Продажи по товарам</b></div>
      {loading && <div>Загрузка…</div>}
      {error && <div style={{color: 'crimson'}}>{error}</div>}
      <table>
        <thead>
          <tr>
            <th>Название товара</th>
            <th>Общее проданное кол-во</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{r.product_name}</td>
              <td>{r.total_sold_qty}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th>Итого</th>
            <th>{totalQty}</th>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

