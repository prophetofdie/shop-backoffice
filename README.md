# Shop Back-Office System

> Административная панель для интернет-магазина  
> (React + FastAPI + MongoDB + Nginx + Docker Compose)

---

## О проекте

Shop Back-Office System — это локальное веб-приложение для менеджеров интернет-магазина.  
Система не предназначена для покупателей и используется для обработки и анализа заказов.

Приложение хранит:
- каталог товаров (название, артикул, цена, остаток на складе),
- базу клиентов,
- заказы с их статусами: Новый, Оплачен, Отгружен.

Функционал включает:
- просмотр списка заказов и товаров,
- фильтрацию заказов по статусу и клиенту,
- детализацию состава заказа,
- отчёт «Продажи по товарам» с суммарными данными.

---

## Технологический стек

| Компонент | Технология |
|------------|-------------|
| Frontend | React (Vite) + TypeScript / JavaScript |
| Backend | FastAPI (Python) |
| Database | MongoDB 4.4 (без AVX — работает на любом CPU) |
| Proxy / Static | Nginx |
| Infra | Docker & Docker Compose |

---

## Быстрый запуск

```bash
# Клонировать проект
git clone https://github.com/YOUR_USERNAME/shop-backoffice.git
cd shop-backoffice

# Запустить всё (Mongo + API + Frontend + Nginx)
make up
```
### Shortcuts

```bash
make up         # собрать и запустить проект
make down       # остановить контейнеры
make restart    # перезапустить проект
make clean      # очистить все контейнеры и volumes
make ps         # показать статус
make logs       # вывести логи всех сервисов
make frontend   # пересобрать только фронт
make backend    # пересобрать только бекенд
```
