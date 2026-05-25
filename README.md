# WG Easy Telegram Bot

🤖 Telegram бот для полного управления WG Easy v15.3.0 с функциями продажи и синхронизации.

## 📋 Возможности

- ✅ **Полная синхронизация** с панелью WG Easy v15.3.0
- ✅ **Управление клиентами**: создание, удаление, активация/деактивация
- ✅ **Продажа ключей**: встроенная система продажи VPN ключей
- ✅ **QR коды**: автоматическая генерация и отправка QR кодов
- ✅ **Config файлы**: выгрузка конфигурационных файлов WireGuard
- ✅ **Статистика**: мониторинг трафика и статуса клиентов
- ✅ **Исчезающее меню**: кнопки обновляются при навигации, не засоряя чат
- ✅ **Безопасность**: защита по ID администраторов

## 🚀 Быстрый старт

### 1. Получение токена бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Введите имя бота (например, `WG Easy Manager`)
4. Введите username бота (должен заканчиваться на `bot`, например `wg_easy_manager_bot`)
5. Сохраните полученный токен

### 2. Узнайте свой Telegram ID

1. Отправьте сообщение боту [@userinfobot](https://t.me/userinfobot)
2. Скопируйте ваш числовой ID

### 3. Установка зависимостей

```bash
pip install python-telegram-bot aiohttp
```

### 4. Настройка переменных окружения

Создайте файл `.env` или экспортируйте переменные:

```bash
# Токен бота от BotFather
export BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

# URL панели WG Easy
export WG_EASY_URL="http://localhost:51821"

# Пароль от панели WG Easy
export WG_EASY_PASSWORD="your_password"

# ID администраторов (через запятую)
export ADMIN_IDS="123456789,987654321"

# Включить продажу (true/false)
export SALE_ENABLED="true"

# Способы оплаты
export PAYMENT_METHODS="Карта: 1234 5678 9012 3456\nСБП: +7 999 123 45 67"
```

### 5. Запуск бота

```bash
python3 bot.py
```

## 🐳 Docker Compose (рекомендуется)

Создайте файл `docker-compose.yml`:

```yaml
version: '3.8'

services:
  wg-easy:
    image: weejewel/wg-easy:latest
    container_name: wg-easy
    restart: unless-stopped
    ports:
      - "51820:51820/udp"
      - "51821:51821/tcp"
    volumes:
      - ./wg-easy:/etc/wireguard
    environment:
      - WG_HOST=your.server.ip
      - PASSWORD=your_password
      - PORT=51821
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1

  wg-bot:
    build: .
    container_name: wg-bot
    restart: unless-stopped
    depends_on:
      - wg-easy
    environment:
      - BOT_TOKEN=your_bot_token
      - WG_EASY_URL=http://wg-easy:51821
      - WG_EASY_PASSWORD=your_password
      - ADMIN_IDS=your_telegram_id
      - SALE_ENABLED=true
      - PAYMENT_METHODS=Карта: 1234 5678 9012 3456
```

Запуск:

```bash
docker-compose up -d
```

## 📱 Использование бота

### Главное меню

После команды `/start` бот покажет главное меню:

- **📊 Статистика** - общая информация о сервере
- **👥 Клиенты** - список всех подключений
- **➕ Создать ключ** - создание нового клиента
- **💰 Продажа** - меню продажи (если включено)
- **🔄 Синхронизация** - обновление данных из WG Easy
- **⚙️ Настройки** - информация о конфигурации

### Создание ключа

1. Нажмите "➕ Создать ключ"
2. Выберите тариф (трафик и срок действия)
3. Введите имя для ключа
4. Бот создаст клиента и отправит QR код

### Управление клиентами

1. Выберите "👥 Клиенты"
2. Кликните на нужного клиента
3. Доступные действия:
   - 📱 QR Код - получить QR для подключения
   - 📄 Config файл - скачать файл конфигурации
   - ⏸️ Деактивировать - временно отключить
   - ❌ Удалить - удалить клиента

### Продажа ключей

При включённой продаже (`SALE_ENABLED=true`):

1. Пользователь видит способы оплаты
2. После оплаты администратор создаёт ключ через бота
3. Ключ отправляется покупателю

## 🔧 API WG Easy v15.3.0

Бот использует следующие эндпоинты WG Easy:

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/api/session` | Аутентификация |
| GET | `/api/wireguard/config` | Получить конфиг |
| POST | `/api/wireguard/client` | Создать клиента |
| DELETE | `/api/wireguard/client/{id}` | Удалить клиента |
| GET | `/api/wireguard/client/{id}/qrCode.svg` | QR код |
| GET | `/api/wireguard/client/{id}/configuration` | Config файл |
| PUT | `/api/wireguard/client/{id}/enable` | Активировать |
| PUT | `/api/wireguard/client/{id}/disable` | Деактивировать |

## 🛡️ Безопасность

- Все запросы к WG Easy аутентифицированы через cookie
- Доступ к боту ограничен по `ADMIN_IDS`
- Переменные окружения не хранятся в коде
- Поддержка HTTPS для WG Easy

## 📝 Пример .env файла

```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
WG_EASY_URL=https://vpn.yourdomain.com
WG_EASY_PASSWORD=SecurePassword123
ADMIN_IDS=123456789,987654321,111222333
SALE_ENABLED=true
PAYMENT_METHODS=💳 Сбербанк: 2202 2000 1234 5678\n💰 СБП: +7 999 123 45 67\n💵 USDT (TRC20): Txxxxxxxxxxxxxxxxxxxx
```

## 🆘 Troubleshooting

### Бот не подключается к WG Easy

- Проверьте правильность `WG_EASY_URL` и `WG_EASY_PASSWORD`
- Убедитесь, что WG Easy доступен из контейнера бота
- Проверьте логи WG Easy на наличие ошибок

### Ошибка аутентификации

- WG Easy v15+ использует cookie-аутентификацию
- Убедитесь, что пароль правильный
- Перезапустите бота после смены пароля

### Бот не отвечает

- Проверьте токен бота
- Убедитесь, что `ADMIN_IDS` содержит ваш ID
- Проверьте логи бота

## 📄 Лицензия

MIT License - свободное использование и модификация.

## 🤝 Contributing

Pull requests приветствуются! 

## 📞 Поддержка

- Создайте issue в репозитории
- Напишите в Telegram (если указано)

---

**Версия WG Easy:** v15.3.0+  
**Версия бота:** 1.0.0  
**Язык:** Python 3.10+