# Makefile для удобного управления проектом

# Links:
links:
	@echo "Swagger UI:  http://127.0.0.1:8000/docs"
	@echo "Main page:   http://localhost:8080"

# Build всего проекта
build:
	docker compose up -d --build

up: build links

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
