# Makefile для удобного управления проектом

# Запуск всего проекта
up:
	docker compose up -d --build

# Остановка контейнеров
down:
	docker compose down

# Просмотр логов
logs:
	docker compose logs -f

# Проверка статуса контейнеров
ps:
	docker compose ps

# Полная очистка (включая volumes и неиспользуемые образы)
clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# Перезапуск проекта
restart: down up

# Только фронтенд пересобрать
frontend:
	docker compose build frontend --no-cache
	docker compose up -d frontend

# Только бэкенд пересобрать
backend:
	docker compose build api --no-cache
	docker compose up -d api
