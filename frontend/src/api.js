// Простой и безопасный выбор базы API:
// 1) Если передали VITE_API_BASE при сборке — используем его.
// 2) Иначе используем относительный "/api" (идёт через nginx proxy).
const envBase = import.meta.env.VITE_API_BASE;
export const API_BASE = (envBase && String(envBase).trim() !== "") ? envBase : "/api";

// Обёртка GET-запроса
export async function getJSON(path) {
  // Комментарий: path должен начинаться со слэша (например, "/products")
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

// Обёртка POST-запроса
export async function postJSON(path, body) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}
