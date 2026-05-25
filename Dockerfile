FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей
RUN pip install --no-cache-dir python-telegram-bot aiohttp

# Копирование файлов бота
COPY bot.py .

# Запуск бота
CMD ["python", "bot.py"]
