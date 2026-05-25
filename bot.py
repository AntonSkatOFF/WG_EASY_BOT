#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WG Easy Bot - Telegram бот для управления WG Easy v15.3.0
Полная синхронизация, продажа ключей, управление клиентами
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, ConversationHandler, MessageHandler, filters
)

# Константы состояний для ConversationHandler
SELECTING_ACTION, CREATING_CLIENT, SETTING_TRAFFIC, SETTING_EXPIRY, \
    SELECTING_CLIENT, CONFIRMING_DELETE, ENTERING_PROMO = range(7)

# Конфигурация
WG_EASY_URL = os.getenv('WG_EASY_URL', 'http://localhost:51821')
WG_EASY_PASSWORD = os.getenv('WG_EASY_PASSWORD', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []
SALE_ENABLED = os.getenv('SALE_ENABLED', 'false').lower() == 'true'
PAYMENT_METHODS = os.getenv('PAYMENT_METHODS', 'Карта: 1234 5678 9012 3456\nСБП: +7 999 123 45 67')

# Глобальное хранилище сессий
user_sessions: Dict[int, Dict[str, Any]] = {}


class WGEasyAPI:
    """Класс для работы с WG Easy API"""
    
    def __init__(self, base_url: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None
        self.cookie: Optional[str] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def authenticate(self) -> bool:
        """Аутентификация в WG Easy"""
        try:
            session = await self._get_session()
            # WG Easy v15+ использует cookie-based auth
            async with session.post(
                f"{self.base_url}/api/session",
                json={'password': self.password},
                headers={'Content-Type': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    # Сохраняем cookie из ответа
                    self.cookie = resp.cookies.get('token', {}).value if resp.cookies.get('token') else None
                    if not self.cookie:
                        # Пробуем получить из заголовков
                        self.cookie = resp.headers.get('Set-Cookie', '').split(';')[0].split('=')[1] if 'Set-Cookie' in resp.headers else None
                    return True
                return False
        except Exception as e:
            print(f"Auth error: {e}")
            return False
    
    async def _get_headers(self) -> Dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.cookie:
            headers['Cookie'] = f'token={self.cookie}'
        return headers
    
    async def get_config(self) -> Dict[str, Any]:
        """Получить полную конфигурацию"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/wireguard/config",
                headers=await self._get_headers()
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}
        except Exception as e:
            print(f"Get config error: {e}")
            return {}
    
    async def get_clients(self) -> list:
        """Получить список клиентов"""
        config = await self.get_config()
        return config.get('clients', [])
    
    async def create_client(self, name: str, traffic_gb: int = 0, expiry_days: int = 0) -> Optional[Dict]:
        """Создать нового клиента"""
        try:
            session = await self._get_session()
            data = {'name': name}
            
            # WG Easy v15+ поддерживает расширенные параметры
            if traffic_gb > 0:
                data['traffic'] = traffic_gb * 1024 * 1024 * 1024  # Конвертация в байты
            
            if expiry_days > 0:
                expiry_date = datetime.now() + timedelta(days=expiry_days)
                data['expireDate'] = expiry_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            async with session.post(
                f"{self.base_url}/api/wireguard/client",
                json=data,
                headers=await self._get_headers()
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            print(f"Create client error: {e}")
            return None
    
    async def delete_client(self, client_id: str) -> bool:
        """Удалить клиента"""
        try:
            session = await self._get_session()
            async with session.delete(
                f"{self.base_url}/api/wireguard/client/{client_id}",
                headers=await self._get_headers()
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"Delete client error: {e}")
            return False
    
    async def get_client_qr(self, client_id: str) -> Optional[str]:
        """Получить QR код клиента"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/wireguard/client/{client_id}/qrCode.svg",
                headers=await self._get_headers()
            ) as resp:
                if resp.status == 200:
                    return await resp.text()
                return None
        except Exception as e:
            print(f"Get QR error: {e}")
            return None
    
    async def get_client_config(self, client_id: str) -> Optional[str]:
        """Получить конфиг файл клиента"""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/wireguard/client/{client_id}/configuration",
                headers=await self._get_headers()
            ) as resp:
                if resp.status == 200:
                    return await resp.text()
                return None
        except Exception as e:
            print(f"Get config error: {e}")
            return None
    
    async def enable_client(self, client_id: str) -> bool:
        """Активировать клиента"""
        try:
            session = await self._get_session()
            async with session.put(
                f"{self.base_url}/api/wireguard/client/{client_id}/enable",
                headers=await self._get_headers()
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"Enable client error: {e}")
            return False
    
    async def disable_client(self, client_id: str) -> bool:
        """Деактивировать клиента"""
        try:
            session = await self._get_session()
            async with session.put(
                f"{self.base_url}/api/wireguard/client/{client_id}/disable",
                headers=await self._get_headers()
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"Disable client error: {e}")
            return False
    
    async def update_client(self, client_id: str, **kwargs) -> bool:
        """Обновить параметры клиента"""
        try:
            session = await self._get_session()
            async with session.put(
                f"{self.base_url}/api/wireguard/client/{client_id}",
                json=kwargs,
                headers=await self._get_headers()
            ) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"Update client error: {e}")
            return False
    
    async def close(self):
        """Закрыть сессию"""
        if self.session and not self.session.closed:
            await self.session.close()


# Глобальный экземпляр API
wg_api = WGEasyAPI(WG_EASY_URL, WG_EASY_PASSWORD)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Основное меню с кнопками"""
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("👥 Клиенты", callback_data="clients_list")],
        [InlineKeyboardButton("➕ Создать ключ", callback_data="create_key")],
        [InlineKeyboardButton("💰 Продажа", callback_data="sale_menu")] if SALE_ENABLED else [],
        [InlineKeyboardButton("🔄 Синхронизация", callback_data="sync")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_clients_keyboard(clients: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком клиентов"""
    keyboard = []
    for client in clients[:10]:  # Показываем максимум 10
        name = client.get('name', 'Unknown')
        client_id = client.get('id', '')
        keyboard.append([InlineKeyboardButton(f"🔑 {name}", callback_data=f"client_{client_id}")])
    
    if len(clients) > 10:
        keyboard.append([InlineKeyboardButton("... и ещё", callback_data="more_clients")])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def get_client_actions_keyboard(client_id: str) -> InlineKeyboardMarkup:
    """Действия с клиентом"""
    keyboard = [
        [InlineKeyboardButton("📱 QR Код", callback_data=f"qr_{client_id}")],
        [InlineKeyboardButton("📄 Config файл", callback_data=f"config_{client_id}")],
        [InlineKeyboardButton("⏸️ Деактивировать", callback_data=f"disable_{client_id}")],
        [InlineKeyboardButton("❌ Удалить", callback_data=f"delete_{client_id}")],
        [InlineKeyboardButton("◀️ Назад к клиентам", callback_data="clients_list")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_create_key_keyboard() -> InlineKeyboardMarkup:
    """Меню создания ключа"""
    keyboard = [
        [InlineKeyboardButton("1 ГБ / 7 дней", callback_data="preset_1_7")],
        [InlineKeyboardButton("5 ГБ / 30 дней", callback_data="preset_5_30")],
        [InlineKeyboardButton("10 ГБ / 30 дней", callback_data="preset_10_30")],
        [InlineKeyboardButton("Безлимит", callback_data="preset_unlimited")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS and ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещён")
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"👋 Привет, {update.effective_user.first_name}!\n\n"
        "WG Easy Bot - управление VPN сервером\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    
    return SELECTING_ACTION


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопок главного меню"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "back_main":
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        return SELECTING_ACTION
    
    elif action == "stats":
        config = await wg_api.get_config()
        clients = config.get('clients', [])
        active = sum(1 for c in clients if c.get('enabled', True))
        
        stats_text = (
            "📊 **Статистика WG Easy**\n\n"
            f"🔹 Всего клиентов: {len(clients)}\n"
            f"🔹 Активных: {active}\n"
            f"🔹 Неактивных: {len(clients) - active}\n\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await query.edit_message_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]])
        )
        return SELECTING_ACTION
    
    elif action == "clients_list":
        clients = await wg_api.get_clients()
        if not clients:
            await query.edit_message_text(
                "📭 Клиентов пока нет",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]])
            )
        else:
            await query.edit_message_text(
                f"👥 **Клиенты** ({len(clients)}):\n\nВыберите клиента:",
                parse_mode='Markdown',
                reply_markup=get_clients_keyboard(clients)
            )
        return SELECTING_ACTION
    
    elif action == "create_key":
        await query.edit_message_text(
            "➕ **Создание нового ключа**\n\nВыберите тариф:",
            parse_mode='Markdown',
            reply_markup=get_create_key_keyboard()
        )
        return CREATING_CLIENT
    
    elif action == "sale_menu":
        if not SALE_ENABLED:
            await query.edit_message_text("💰 Продажа отключена")
            return SELECTING_ACTION
        
        await query.edit_message_text(
            "💰 **Продажа VPN ключей**\n\n"
            f"Способы оплаты:\n{PAYMENT_METHODS}\n\n"
            "Отправьте /pay для создания заказа",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
            ])
        )
        return SELECTING_ACTION
    
    elif action == "sync":
        await query.answer("🔄 Синхронизация...")
        config = await wg_api.get_config()
        clients = config.get('clients', [])
        
        await query.edit_message_text(
            f"✅ **Синхронизация завершена**\n\n"
            f"Загружено клиентов: {len(clients)}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]])
        )
        return SELECTING_ACTION
    
    elif action == "settings":
        await query.edit_message_text(
            "⚙️ **Настройки**\n\n"
            f"WG Easy URL: {WG_EASY_URL}\n"
            f"Продажа: {'✅ Вкл' if SALE_ENABLED else '❌ Выкл'}\n\n"
            "Для изменения настроек используйте переменные окружения",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]])
        )
        return SELECTING_ACTION
    
    return SELECTING_ACTION


async def preset_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор пресета при создании ключа"""
    query = update.callback_query
    await query.answer()
    
    presets = {
        'preset_1_7': (1, 7),
        'preset_5_30': (5, 30),
        'preset_10_30': (10, 30),
        'preset_unlimited': (0, 0)
    }
    
    preset = presets.get(query.data, (0, 0))
    context.user_data['traffic_gb'] = preset[0]
    context.user_data['expiry_days'] = preset[1]
    
    await query.edit_message_text(
        "➕ **Создание ключа**\n\n"
        f"Трафик: {preset[0]} ГБ (0 = безлимит)\n"
        f"Срок: {preset[1]} дней (0 = безлимит)\n\n"
        "Введите имя для ключа:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Отмена", callback_data="back_main")]])
    )
    
    return SETTING_TRAFFIC


async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод имени клиента"""
    name = update.message.text.strip()
    context.user_data['client_name'] = name
    
    # Удаляем сообщение с именем
    await update.message.delete()
    
    traffic_gb = context.user_data.get('traffic_gb', 0)
    expiry_days = context.user_data.get('expiry_days', 0)
    
    # Создаём клиента
    await update.message.reply_text("⏳ Создание ключа...")
    
    client = await wg_api.create_client(name, traffic_gb, expiry_days)
    
    if client:
        client_id = client.get('id', '')
        
        # Получаем QR код
        qr_svg = await wg_api.get_client_qr(client_id)
        
        response_text = (
            f"✅ **Ключ создан!**\n\n"
            f"🔑 Имя: {name}\n"
            f"📊 Трафик: {traffic_gb} ГБ\n"
            f"📅 Срок: {expiry_days} дн.\n\n"
            "QR код для подключения:"
        )
        
        if qr_svg:
            # Сохраняем QR как файл
            import io
            qr_file = io.BytesIO(qr_svg.encode('utf-8'))
            qr_file.name = f"{name}_qr.svg"
            
            await update.message.reply_photo(
                photo=qr_file,
                caption=response_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В меню", callback_data="back_main")]])
            )
        else:
            await update.message.reply_text(
                response_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В меню", callback_data="back_main")]])
            )
    else:
        await update.message.reply_text(
            "❌ Ошибка при создании ключа",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В меню", callback_data="back_main")]])
        )
    
    context.user_data.clear()
    return SELECTING_ACTION


async def client_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор конкретного клиента"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "more_clients":
        await query.answer("Показаны первые 10 клиентов")
        return SELECTING_ACTION
    
    if not query.data.startswith("client_"):
        return SELECTING_ACTION
    
    client_id = query.data.replace("client_", "")
    clients = await wg_api.get_clients()
    client = next((c for c in clients if c.get('id') == client_id), None)
    
    if not client:
        await query.edit_message_text("❌ Клиент не найден")
        return SELECTING_ACTION
    
    name = client.get('name', 'Unknown')
    enabled = client.get('enabled', True)
    traffic = client.get('traffic', {})
    transfer_down = traffic.get('transferDown', 0) / (1024*1024)  # MB
    transfer_up = traffic.get('transferUp', 0) / (1024*1024)
    
    status = "🟢 Активен" if enabled else "🔴 Неактивен"
    
    await query.edit_message_text(
        f"🔑 **{name}**\n\n"
        f"Статус: {status}\n"
        f"⬇️ Скачано: {transfer_down:.2f} MB\n"
        f"⬆️ Загружено: {transfer_up:.2f} MB\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=get_client_actions_keyboard(client_id)
    )
    
    return SELECTING_ACTION


async def client_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Действие с клиентом"""
    query = update.callback_query
    await query.answer()
    
    action_parts = query.data.split('_')
    action = action_parts[0]
    client_id = '_'.join(action_parts[1:])
    
    if action == "qr":
        qr_svg = await wg_api.get_client_qr(client_id)
        if qr_svg:
            import io
            qr_file = io.BytesIO(qr_svg.encode('utf-8'))
            qr_file.name = f"{client_id}_qr.svg"
            
            await query.message.reply_photo(
                photo=qr_file,
                caption=f"📱 QR код для подключения"
            )
        
        await query.edit_message_text(
            "✅ QR код отправлен",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="clients_list")]])
        )
    
    elif action == "config":
        config_content = await wg_api.get_client_config(client_id)
        if config_content:
            import io
            config_file = io.BytesIO(config_content.encode('utf-8'))
            config_file.name = f"{client_id}.conf"
            
            await query.message.reply_document(
                document=config_file,
                caption="📄 Конфигурационный файл"
            )
        
        await query.edit_message_text(
            "✅ Конфиг отправлен",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="clients_list")]])
        )
    
    elif action == "disable":
        clients = await wg_api.get_clients()
        client = next((c for c in clients if c.get('id') == client_id), None)
        
        if client:
            if client.get('enabled', True):
                await wg_api.disable_client(client_id)
                await query.answer("⏸️ Деактивирован")
            else:
                await wg_api.enable_client(client_id)
                await query.answer("▶️ Активирован")
        
        await client_selected(update, context)
    
    elif action == "delete":
        context.user_data['delete_client_id'] = client_id
        await query.edit_message_text(
            "❌ **Вы уверены?**\n\nЭто действие нельзя отменить.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_delete")],
                [InlineKeyboardButton("❌ Отмена", callback_data="clients_list")]
            ])
        )
        return CONFIRMING_DELETE
    
    return SELECTING_ACTION


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение удаления"""
    query = update.callback_query
    await query.answer()
    
    client_id = context.user_data.get('delete_client_id')
    if client_id:
        success = await wg_api.delete_client(client_id)
        if success:
            await query.edit_message_text("✅ Клиент удалён")
        else:
            await query.edit_message_text("❌ Ошибка при удалении")
    
    context.user_data.clear()
    return SELECTING_ACTION


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия"""
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text(
        "❌ Отменено",
        reply_markup=get_main_menu_keyboard()
    )
    
    return SELECTING_ACTION


async def post_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаление меню после выбора"""
    if update.callback_query:
        # Меню уже обновлено callback handler
        pass


def main():
    """Основная функция"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не установлен!")
        return
    
    # Аутентификация в WG Easy
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(wg_api.authenticate())
        print("✅ Подключено к WG Easy")
    except Exception as e:
        print(f"❌ Ошибка подключения к WG Easy: {e}")
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавление handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(menu_callback),
                CallbackQueryHandler(client_selected, pattern='^client_'),
                CallbackQueryHandler(client_action, pattern='^(qr|config|disable|delete)_'),
            ],
            CREATING_CLIENT: [
                CallbackQueryHandler(preset_selected),
            ],
            SETTING_TRAFFIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name),
                CallbackQueryHandler(menu_callback),
            ],
            SELECTING_CLIENT: [
                CallbackQueryHandler(client_selected),
            ],
            CONFIRMING_DELETE: [
                CallbackQueryHandler(confirm_delete, pattern='^confirm_delete$'),
                CallbackQueryHandler(client_action),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    
    application.add_handler(conv_handler)
    
    # Запуск бота
    print("🤖 Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
