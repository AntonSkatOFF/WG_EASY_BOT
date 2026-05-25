# 🧪 Инструкция по тестированию WG Easy Bot

## Перед началом тестирования

### 1. Подготовка окружения

```bash
# Установите зависимости
pip install -r requirements.txt

# Или создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Для Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Получение тестовых данных

#### A. Токен бота (обязательно)
1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите имя: `Test WG Easy Bot`
4. Введите username: `test_wg_easy_ваш_username_bot`
5. **Сохраните токен** (выглядит как: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### B. Ваш Telegram ID
1. Откройте [@userinfobot](https://t.me/userinfobot)
2. Нажмите Start
3. **Запишите ваш ID** (число, например: `123456789`)

#### C. WG Easy панель (опционально для полного теста)

**Вариант 1: Использовать существующую панель**
- Если у вас уже есть WG Easy, запишите:
  - URL (например: `http://localhost:51821` или `https://vpn.yourdomain.com`)
  - Пароль от панели

**Вариант 2: Запустить тестовый WG Easy в Docker**
```bash
docker run -d \
  --name wg-easy-test \
  -e WG_HOST=0.0.0.0 \
  -e PASSWORD=test123 \
  -p 51820:51820/udp \
  -p 51821:51821/tcp \
  --cap-add=NET_ADMIN \
  --sysctl="net.ipv4.ip_forward=1" \
  weejewel/wg-easy:latest
```

---

## 📋 Этапы тестирования

### Этап 1: Базовое тестирование (без WG Easy)

Создайте файл `.env` для теста:

```bash
cat > .env << EOF
BOT_TOKEN=ВАШ_ТОКЕН_ОТ_BOTFATHER
WG_EASY_URL=http://localhost:51821
WG_EASY_PASSWORD=test123
ADMIN_IDS=ВАШ_TELEGRAM_ID
SALE_ENABLED=true
PAYMENT_METHODS=Карта: 1111 2222 3333 4444\nСБП: +7 999 000 00 00
EOF
```

**Запуск бота:**
```bash
python3 bot.py
```

**Что проверять:**
1. ✅ Бот запускается без ошибок
2. ✅ В консоли видно "Bot started..."
3. ✅ Бот подключается к Telegram API

**Тесты в Telegram:**

| Действие | Ожидаемый результат |
|----------|---------------------|
| Отправить `/start` | Бот отвечает приветствием и показывает главное меню |
| Нажать "📊 Статистика" | Показывается статистика (может быть ошибка WG Easy - это нормально) |
| Нажать "◀️ Назад" | Меню возвращается к главному |
| Нажать "👥 Клиенты" | Показывается список клиентов или сообщение "Клиентов пока нет" |
| Нажать "➕ Создать ключ" | Показывается выбор тарифа |
| Нажать любой тариф | Бот просит ввести имя ключа |

**Если бот не отвечает:**
- Проверьте токен в `.env`
- Проверьте, что ваш ID указан в `ADMIN_IDS`
- Посмотрите логи бота в консоли

---

### Этап 2: Тестирование с WG Easy панелью

#### 2.1. Настройка подключения

Если WG Easy запущен в Docker, обновите `.env`:

```bash
# Для Docker (бот в той же сети)
WG_EASY_URL=http://host.docker.internal:51821  # macOS/Windows
# ИЛИ
WG_EASY_URL=http://172.17.0.1:51821  # Linux

# Для локального запуска
WG_EASY_URL=http://localhost:51821
```

#### 2.2. Проверка подключения к WG Easy

Создайте тестовый скрипт `test_wg_connection.py`:

```python
#!/usr/bin/env python3
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_wg_easy():
    url = os.getenv('WG_EASY_URL', 'http://localhost:51821')
    password = os.getenv('WG_EASY_PASSWORD', '')
    
    print(f"🔌 Подключение к {url}...")
    
    async with aiohttp.ClientSession() as session:
        # Аутентификация
        async with session.post(
            f"{url}/api/session",
            json={'password': password},
            headers={'Content-Type': 'application/json'}
        ) as resp:
            print(f"📝 Аутентификация: {resp.status}")
            if resp.status == 200:
                print("✅ Успешно!")
                cookie = resp.cookies.get('token')
                print(f"🍪 Cookie: {cookie.value if cookie else 'Не получен'}")
            else:
                print(f"❌ Ошибка: {await resp.text()}")
                return
        
        # Получение конфига
        headers = {'Content-Type': 'application/json'}
        if cookie:
            headers['Cookie'] = f'token={cookie.value}'
        
        async with session.get(
            f"{url}/api/wireguard/config",
            headers=headers
        ) as resp:
            print(f"📊 Получение конфига: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                clients = data.get('clients', [])
                print(f"✅ Найдено клиентов: {len(clients)}")
                for client in clients[:3]:
                    print(f"   - {client.get('name', 'Unknown')}")
            else:
                print(f"❌ Ошибка: {await resp.text()}")

if __name__ == '__main__':
    asyncio.run(test_wg_easy())
```

Запустите:
```bash
pip install python-dotenv
python3 test_wg_connection.py
```

#### 2.3. Полное тестирование бота

**Чек-лист функциональности:**

| Функция | Как тестировать | Ожидаемый результат |
|---------|-----------------|---------------------|
| **Статистика** | Главное меню → 📊 Статистика | Показывает количество клиентов, активных/неактивных |
| **Список клиентов** | 👥 Клиенты | Список всех клиентов WG Easy с кнопками |
| **QR код** | Выбрать клиента → 📱 QR Код | Отправляет SVG изображение QR кода |
| **Config файл** | Выбрать клиента → 📄 Config файл | Отправляет файл `.conf` для скачивания |
| **Деактивация** | Выбрать клиента → ⏸️ Деактивировать | Клиент деактивируется в WG Easy |
| **Удаление** | Выбрать клиента → ❌ Удалить → Подтвердить | Клиент удаляется из WG Easy |
| **Создание ключа** | ➕ Создать ключ → Выбрать тариф → Ввести имя | Создаётся новый клиент, отправляется QR |
| **Синхронизация** | 🔄 Синхронизация | Обновление данных, показывается количество клиентов |
| **Настройки** | ⚙️ Настройки | Показывает текущую конфигурацию |

---

### Этап 3: Тестирование продажи ключей

1. Убедитесь, что `SALE_ENABLED=true` в `.env`
2. Перезапустите бота
3. В главном меню должна появиться кнопка "💰 Продажа"

**Тестовый сценарий:**
1. Нажмите "💰 Продажа"
2. Проверьте, что отображаются способы оплаты из `PAYMENT_METHODS`
3. Проверьте кнопку "◀️ Назад"

---

### Этап 4: Тестирование исчезающего меню

**Критически важно для вашего требования!**

1. Отправьте `/start`
2. Нажмите "📊 Статистика"
3. **Проверьте:** старое сообщение с меню должно **исчезнуть** (обновиться), а не остаться в чате
4. Нажмите "◀️ Назад"
5. **Проверьте:** снова должно обновиться то же сообщение
6. Повторите для всех пунктов меню

**Если сообщения не исчезают:**
- ✅ Правильно: используется `edit_message_text`
- ❌ Неправильно: используется `reply_text` или `send_message`

В нашем боте реализовано правильное поведение через `query.edit_message_text()`.

---

### Этап 5: Тестирование безопасности

1. Попросите другого пользователя (не из `ADMIN_IDS`) отправить `/start`
2. **Ожидаемый результат:** "❌ Доступ запрещён"
3. Проверьте, что бот игнорирует команды от неавторизованных пользователей

---

### Этап 6: Docker тестирование

Создайте `docker-compose.test.yml`:

```yaml
version: '3.8'

services:
  wg-easy-test:
    image: weejewel/wg-easy:latest
    container_name: wg-easy-test
    environment:
      - WG_HOST=0.0.0.0
      - PASSWORD=test123
      - PORT=51821
    ports:
      - "51820:51820/udp"
      - "51821:51821/tcp"
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1

  wg-bot-test:
    build: .
    container_name: wg-bot-test
    depends_on:
      - wg-easy-test
    environment:
      - BOT_TOKEN=ВАШ_ТОКЕН
      - WG_EASY_URL=http://wg-easy-test:51821
      - WG_EASY_PASSWORD=test123
      - ADMIN_IDS=ВАШ_ID
      - SALE_ENABLED=true
```

Запуск:
```bash
docker-compose -f docker-compose.test.yml up -d
```

Просмотр логов:
```bash
docker logs -f wg-bot-test
```

---

## 🐛 Отладка распространённых проблем

### Проблема 1: "No module named 'telegram'"
**Решение:**
```bash
pip install python-telegram-bot==20.0
```

### Проблема 2: Бот не подключается к WG Easy
**Диагностика:**
```bash
# Проверьте доступность WG Easy
curl http://localhost:51821/api/session -X POST -H "Content-Type: application/json" -d '{"password":"your_password"}'

# Проверьте логи WG Easy
docker logs wg-easy
```

### Проблема 3: Ошибка аутентификации
**Причины:**
- Неправильный пароль
- WG Easy требует HTTPS
- Cookie не передаются корректно

**Решение:**
1. Проверьте пароль в панели WG Easy
2. Для HTTPS используйте полный URL: `https://your-domain.com`
3. Перезапустите бота

### Проблема 4: Кнопки не исчезают
**Причина:** Используется `send_message` вместо `edit_message_text`

**Проверка кода:**
```bash
grep -n "edit_message_text" bot.py  # Должно быть много совпадений
grep -n "send_message" bot.py       # Должно быть 0 или минимум
```

---

## ✅ Финальный чек-лист перед публикацией

- [ ] Бот запускается без ошибок
- [ ] Команда `/start` работает
- [ ] Все кнопки главного меню работают
- [ ] Исчезающее меню работает (сообщения обновляются, не дублируются)
- [ ] Подключение к WG Easy установлено
- [ ] Создание клиентов работает
- [ ] QR коды генерируются
- [ ] Config файлы скачиваются
- [ ] Удаление клиентов работает
- [ ] Статистика отображается
- [ ] Безопасность работает (доступ только для ADMIN_IDS)
- [ ] Режим продажи работает (если включён)
- [ ] Docker сборка работает
- [ ] Файл `.env.example` содержит все переменные
- [ ] README.md актуален и подробен
- [ ] Файл `.gitignore` исключает `.env` и `__pycache__`

---

## 📊 Пример успешного теста

```
✅ Bot started...
🔌 WG Easy connected: http://localhost:51821
👤 Admin IDs: [123456789]
💰 Sale mode: enabled

[Telegram]
User: @yourusername
/start → Приветствие + меню
📊 Статистика → "Всего клиентов: 5, Активных: 3"
◀️ Назад → Главное меню
➕ Создать ключ → Выбор тарифа
5 ГБ / 30 дней → "Введите имя для ключа:"
test-client → ✅ Ключ создан + QR код
```

---

## 🚀 Публикация на GitHub

После успешного тестирования:

```bash
# Инициализация git (если ещё не сделана)
git init
git add .
git commit -m "Initial commit: WG Easy Telegram Bot v1.0"

# Создание репозитория на GitHub
# 1. Зайдите на https://github.com/new
# 2. Создайте репозиторий (например, wg-easy-telegram-bot)
# 3. Скопируйте URL репозитория

# Привязка remote и публикация
git remote add origin https://github.com/ВАШ_USERNAME/wg-easy-telegram-bot.git
git branch -M main
git push -u origin main
```

**Добавьте в описание репозитория:**
```
🤖 Telegram бот для управления WG Easy v15.3.0
• Полная синхронизация с панелью
• Продажа VPN ключей
• Исчезающее меню (не засоряет чат)
• QR коды и config файлы
• Docker поддержка
```

---

## 📞 Если что-то пошло не так

1. Проверьте логи бота в консоли
2. Включите debug режим в коде (добавьте `logging.basicConfig(level=logging.DEBUG)`)
3. Проверьте версию `python-telegram-bot` (должна быть >= 20.0)
4. Убедитесь, что WG Easy v15.3.0+ доступен

**Полезные команды для отладки:**
```bash
# Проверка версии Python
python3 --version

# Проверка установленных пакетов
pip list | grep telegram

# Запуск с подробными логами
PYTHONPATH=. python3 -u bot.py 2>&1 | tee bot.log
```

---

**Удачи с тестированием! 🎉**
