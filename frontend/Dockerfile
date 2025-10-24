# --- ЭТАП 1: сборка фронтенда (Node) ---
FROM node:20-slim AS build

# Рабочая директория
WORKDIR /app

# Копируем пакеты отдельно — для кеширования
COPY package.json package-lock.json* ./
RUN npm ci

# Копируем весь фронт
COPY . .

# (Опционально) пробрасываем BASE API на сборке. Не обязателен, т.к. будем использовать относительный /api
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}

# Собираем статику в dist/
RUN npm run build


# --- ЭТАП 2: nginx — отдаём статику и проксируем /api ---
FROM nginx:1.27-alpine AS runtime

# Удаляем дефолтный конфиг и кладём наш
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Кладём собранную статику
COPY --from=build /app/dist /usr/share/nginx/html

# Логи (удобно дебажить локально)
# tail -f /var/log/nginx/app_access.log
# tail -f /var/log/nginx/app_error.log

EXPOSE 80
# Старт nginx — команда уже есть в базовом образе
