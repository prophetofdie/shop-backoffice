# Лёгкий образ Python, 3.10 
FROM python:3.10-slim

# Не создавать .pyc и буферизовать вывод
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Рабочая директория внутри контейнера
WORKDIR /app

# Сначала зависимости — лучше кэшируются
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY . .

# Открываем порт Uvicorn
EXPOSE 8000

# Запуск приложения
# комментарий: слушаем все интерфейсы, чтобы nginx-прокси внутри сети достучался
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
