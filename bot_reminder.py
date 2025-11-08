import asyncio
import aiohttp
import json
import sqlite3
import os
import ssl
from datetime import datetime, timedelta

print("🐱 БОТ-НАПОМИНАЛКА С КОТИКАМИ (SSL FIXED)")
print("=" * 50)

class MedicationReminderBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        self.reminder_tasks = {}
        
        # Инициализация базы данных
        self.init_database()
        
    def init_database(self):
        """Создает базу данных для хранения настроек пользователей"""
        self.conn = sqlite3.connect('reminder_bot.db', check_same_thread=False)
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                is_active INTEGER DEFAULT 1,
                reminder_time TEXT DEFAULT '22:00',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        print("✅ База данных инициализирована")
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def create_ssl_context(self):
        """Создает SSL контекст с отключенной проверкой сертификатов"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    
    async def make_request(self, method, data=None):
        """Отправляет запрос к Telegram API с обходом SSL ошибок"""
        url = f"{self.base_url}/{method}"
        
        try:
            # Создаем SSL контекст без проверки сертификатов
            ssl_context = self.create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                if data:
                    # Для отправки фото используем form-data
                    if 'photo' in data and data['photo'].startswith('http'):
                        async with session.post(url, data=data, timeout=30) as response:
                            return await response.json()
                    else:
                        async with session.post(url, json=data, timeout=30) as response:
                            return await response.json()
                else:
                    async with session.get(url, timeout=30) as response:
                        return await response.json()
        except Exception as e:
            self.log(f"❌ Ошибка запроса: {e}")
            return None
    
    async def send_message(self, chat_id, text, reply_markup=None):
        """Отправляет сообщение пользователю"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
            
        return await self.make_request("sendMessage", data)
    
    async def send_photo(self, chat_id, photo_url, caption=""):
        """Отправляет фото по URL"""
        try:
            data = {
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption
            }
            result = await self.make_request("sendPhoto", data)
            
            if result and result.get('ok'):
                self.log(f"✅ Фото отправлено пользователю {chat_id}")
                return True
            else:
                self.log(f"❌ Ошибка отправки фото: {result}")
                # Пробуем отправить сообщение с ссылкой как фолбэк
                fallback_msg = f"{caption}\n\n📸 Ссылка на котика: {photo_url}"
                await self.send_message(chat_id, fallback_msg)
                return False
                
        except Exception as e:
            self.log(f"❌ Ошибка в send_photo: {e}")
            # Фолбэк - отправляем просто сообщение с ссылкой
            fallback_msg = f"{caption}\n\n📸 Ссылка на котика: {photo_url}"
            await self.send_message(chat_id, fallback_msg)
            return False
    
    async def get_updates(self):
        """Получает обновления от Telegram"""
        url = f"{self.base_url}/getUpdates?offset={self.last_update_id + 1}&timeout=10"
        
        try:
            ssl_context = self.create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=20) as response:
                    result = await response.json()
                    return result.get("result", [])
        except Exception as e:
            self.log(f"❌ Ошибка получения обновлений: {e}")
            return []
    
    def get_user_settings(self, user_id):
        """Получает настройки пользователя"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM user_settings WHERE user_id = ?", 
            (user_id,)
        )
        result = cursor.fetchone()
        
        if result:
            return {
                'user_id': result[0],
                'chat_id': result[1],
                'is_active': bool(result[2]),
                'reminder_time': result[3]
            }
        return None
    
    def save_user_settings(self, user_id, chat_id, is_active=True, reminder_time="22:00"):
        """Сохраняет настройки пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_settings 
            (user_id, chat_id, is_active, reminder_time) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, chat_id, int(is_active), reminder_time))
        
        self.conn.commit()
        self.log(f"💾 Сохранены настройки для пользователя {user_id}")
    
    async def get_random_cat_image(self):
        """Получает случайное фото котика"""
        cat_apis = [
            "https://api.thecatapi.com/v1/images/search",
            "https://cataas.com/cat?json=true"
        ]
        
        for api_url in cat_apis:
            try:
                self.log(f"🔄 Пробуем получить котика из {api_url}")
                ssl_context = self.create_ssl_context()
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(api_url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if "thecatapi.com" in api_url:
                                image_url = data[0].get('url', '')
                                self.log(f"✅ Получен котик от TheCatAPI: {image_url[:50]}...")
                                return image_url
                            elif "cataas.com" in api_url:
                                image_url = f"https://cataas.com{data.get('url', '')}"
                                self.log(f"✅ Получен котик от Cataas: {image_url}")
                                return image_url
                        else:
                            self.log(f"❌ API {api_url} вернул статус {response.status}")
                            
            except Exception as e:
                self.log(f"❌ Ошибка получения котика из {api_url}: {e}")
                continue
        
        # Фолбэк - статичная картинка
        fallback_url = "https://cataas.com/cat"
        self.log(f"🔄 Используем фолбэк котика: {fallback_url}")
        return fallback_url
    
    def create_main_keyboard(self):
        """Создает основную клавиатуру"""
        return {
            "keyboard": [
                ["✅ Включить напоминания", "❌ Выключить напоминания"],
                ["⚙️ Настроить время", "📊 Статус"],
                ["🐱 Получить котика сейчас", "ℹ️ Помощь"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
    
    def create_time_keyboard(self):
        """Создает клавиатуру для выбора времени"""
        times = [
            ["21:00", "21:30"],
            ["22:00", "22:30"], 
            ["23:00", "23:30"],
            ["Назад"]
        ]
        
        return {
            "keyboard": times,
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
    
    async def send_reminder(self, user_id, chat_id):
        """Отправляет напоминание с котиком"""
        try:
            # Получаем случайного котика
            cat_url = await self.get_random_cat_image()
            
            # Отправляем напоминание
            message = (
                "⏰ <b>Время выпить таблетки!</b> 💊\n\n"
                "Не забудьте принять лекарство! 🏥\n"
                "А чтобы поднять настроение - вот вам котик! 🐱"
            )
            
            await self.send_message(chat_id, message)
            await self.send_photo(chat_id, cat_url, "😻 Держите вашего терапевтического котика!")
            
            self.log(f"📨 Отправлено напоминание пользователю {user_id}")
            
        except Exception as e:
            self.log(f"❌ Ошибка отправки напоминания: {e}")
    
    async def start_reminder_for_user(self, user_id, chat_id, reminder_time="22:00"):
        """Запускает ежедневное напоминание для пользователя"""
        if user_id in self.reminder_tasks:
            self.reminder_tasks[user_id].cancel()
        
        async def daily_reminder():
            while True:
                try:
                    now = datetime.now()
                    target_time = datetime.strptime(reminder_time, "%H:%M").time()
                    
                    # Вычисляем время до следующего напоминания
                    target_datetime = datetime.combine(now.date(), target_time)
                    if now.time() > target_time:
                        target_datetime += timedelta(days=1)
                    
                    wait_seconds = (target_datetime - now).total_seconds()
                    
                    self.log(f"⏰ Пользователь {user_id}: ждем {wait_seconds:.0f} сек до {reminder_time}")
                    
                    # Ждем до времени напоминания
                    await asyncio.sleep(wait_seconds)
                    
                    # Проверяем, что напоминание все еще активно
                    settings = self.get_user_settings(user_id)
                    if settings and settings['is_active']:
                        await self.send_reminder(user_id, chat_id)
                    
                    # Ждем до следующего дня
                    await asyncio.sleep(60)  # Небольшая задержка перед следующим циклом
                    
                except asyncio.CancelledError:
                    self.log(f"🛑 Напоминание отменено для пользователя {user_id}")
                    break
                except Exception as e:
                    self.log(f"❌ Ошибка в напоминании: {e}")
                    await asyncio.sleep(3600)  # Ждем час при ошибке
        
        task = asyncio.create_task(daily_reminder())
        self.reminder_tasks[user_id] = task
        self.log(f"✅ Запущено напоминание для {user_id} в {reminder_time}")
    
    async def stop_reminder_for_user(self, user_id):
        """Останавливает напоминание для пользователя"""
        if user_id in self.reminder_tasks:
            self.reminder_tasks[user_id].cancel()
            del self.reminder_tasks[user_id]
            self.log(f"🛑 Остановлено напоминание для пользователя {user_id}")
    
    async def process_message(self, message):
        """Обрабатывает входящие сообщения"""
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text", "")
        
        self.log(f"📨 Сообщение от {user_id}: {text}")
        
        # Получаем или создаем настройки пользователя
        settings = self.get_user_settings(user_id)
        if not settings:
            self.save_user_settings(user_id, chat_id)
            settings = self.get_user_settings(user_id)
        
        if text == "/start" or text == "ℹ️ Помощь":
            response = (
                "🐱 <b>Бот-напоминалка с котиками</b> 💊\n\n"
                "Я буду напоминать вам выпить таблетки каждый день в указанное время "
                "и радовать фотографиями котиков! 😻\n\n"
                "<b>Команды:</b>\n"
                "✅ Включить напоминания - запустить ежедневные напоминания\n"
                "❌ Выключить напоминания - остановить напоминания\n"
                "⚙️ Настроить время - изменить время напоминания\n"
                "📊 Статус - посмотреть текущие настройки\n"
                "🐱 Получить котика сейчас - мгновенная доза котикотерапии\n\n"
                "Для начала нажмите «✅ Включить напоминания»!"
            )
            await self.send_message(chat_id, response, self.create_main_keyboard())
            
        elif text == "✅ Включить напоминания":
            self.save_user_settings(user_id, chat_id, is_active=True)
            await self.start_reminder_for_user(user_id, chat_id, settings['reminder_time'])
            
            response = (
                f"✅ <b>Напоминания включены!</b>\n\n"
                f"Я буду напоминать вам каждый день в <b>{settings['reminder_time']}</b>\n"
                f"Не забудьте выпить таблетки! 💊"
            )
            await self.send_message(chat_id, response, self.create_main_keyboard())
            
        elif text == "❌ Выключить напоминания":
            self.save_user_settings(user_id, chat_id, is_active=False)
            await self.stop_reminder_for_user(user_id)
            
            response = "❌ <b>Напоминания выключены</b>\nВы всегда можете включить их снова!"
            await self.send_message(chat_id, response, self.create_main_keyboard())
            
        elif text == "⚙️ Настроить время":
            response = "🕐 Выберите время для ежедневного напоминания:"
            await self.send_message(chat_id, response, self.create_time_keyboard())
            
        elif text in ["21:00", "21:30", "22:00", "22:30", "23:00", "23:30"]:
            self.save_user_settings(user_id, chat_id, reminder_time=text)
            
            # Перезапускаем напоминание с новым временем
            if settings['is_active']:
                await self.start_reminder_for_user(user_id, chat_id, text)
            
            response = f"🕐 <b>Время установлено!</b>\nНапоминания будут в <b>{text}</b>"
            await self.send_message(chat_id, response, self.create_main_keyboard())
            
        elif text == "Назад":
            await self.send_message(chat_id, "Возвращаемся в главное меню:", self.create_main_keyboard())
            
        elif text == "📊 Статус":
            status = "🟢 ВКЛЮЧЕНЫ" if settings['is_active'] else "🔴 ВЫКЛЮЧЕНЫ"
            response = (
                f"📊 <b>Текущие настройки:</b>\n\n"
                f"• Напоминания: <b>{status}</b>\n"
                f"• Время: <b>{settings['reminder_time']}</b>\n"
                f"• Следующее напоминание: <b>сегодня в {settings['reminder_time']}</b>"
            )
            await self.send_message(chat_id, response, self.create_main_keyboard())
            
        elif text == "🐱 Получить котика сейчас":
            try:
                await self.send_message(chat_id, "🔄 Ищу котика для вас...")
                cat_url = await self.get_random_cat_image()
                self.log(f"🐱 Отправка котика пользователю {user_id}: {cat_url}")
                success = await self.send_photo(chat_id, cat_url, "😻 Ваш внеочередной котик!")
                if not success:
                    await self.send_message(chat_id, "❌ Не удалось загрузить изображение котика, но вот ссылка выше!")
            except Exception as e:
                self.log(f"❌ Ошибка получения котика: {e}")
                await self.send_message(chat_id, "❌ Не удалось получить котика, попробуйте позже")
                
        else:
            response = "🤔 Не понимаю команду. Используйте кнопки ниже или /start для помощи"
            await self.send_message(chat_id, response, self.create_main_keyboard())
    
    async def restore_reminders(self):
        """Восстанавливает напоминания при запуске бота"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id, chat_id, reminder_time FROM user_settings WHERE is_active = 1")
        
        active_users = cursor.fetchall()
        
        for user_id, chat_id, reminder_time in active_users:
            await self.start_reminder_for_user(user_id, chat_id, reminder_time)
            self.log(f"♻️ Восстановлено напоминание для {user_id} в {reminder_time}")
    
    async def run(self):
        """Главный цикл бота"""
        self.log("🔄 Запуск бота-напоминалки...")
        
        # Тест подключения
        test = await self.make_request("getMe")
        if test and test.get("ok"):
            self.log("✅ Подключение к Telegram API успешно!")
            bot_info = test["result"]
            self.log(f"🤖 Бот: @{bot_info.get('username', 'N/A')} ({bot_info.get('first_name', 'N/A')})")
        else:
            self.log("❌ Ошибка подключения. Проверьте токен.")
            self.log("⚠️ Продолжаем работу в надежде, что токен правильный...")
        
        # Восстанавливаем активные напоминания
        await self.restore_reminders()
        
        self.log("🎯 Бот готов к работе!")
        self.log("💊 Напоминания восстановлены для активных пользователей")
        
        try:
            while True:
                updates = await self.get_updates()
                
                for update in updates:
                    self.last_update_id = update["update_id"]
                    if "message" in update:
                        await self.process_message(update["message"])
                
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.log("🛑 Остановка бота")
        except Exception as e:
            self.log(f"💥 Критическая ошибка: {e}")
        finally:
            # Закрываем соединение с БД
            self.conn.close()

def get_token():
    """Получает токен бота из переменных окружения Railway"""
    # Пробуем получить токен из переменных окружения Railway
    token = os.environ.get('BOT_TOKEN')
    
    if token:
        print("✅ Токен получен из переменных окружения Railway")
        return token
    
    # Если запускаем локально, пробуем файл .env
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('BOT_TOKEN='):
                    found_token = line.strip().split('=', 1)[1]
                    print("✅ Токен получен из файла .env")
                    return found_token
    except:
        pass
    
    # Если токен не найден нигде
    print("❌ ТОКЕН БОТА НЕ НАЙДЕН!")
    print("\n📝 КАК ИСПРАВИТЬ:")
    print("1. Для Railway: добавьте переменную BOT_TOKEN в настройках проекта")
    print("2. Для локального запуска: создайте файл .env с содержимым: BOT_TOKEN=ваш_токен")
    print("\n⚡ Получите токен у @BotFather в Telegram")
    
    return None

if __name__ == "__main__":
    print("=" * 50)
    print("🐱 TELEGRAM БОТ-НАПОМИНАЛКА (RAILWAY VERSION)")
    print("💊 Ежедневные напоминания + котики!")
    print("=" * 50)
    
    token = get_token()
    if not token:
        print("❌ Не удалось получить токен бота. Завершение работы.")
        exit(1)
    
    bot = MedicationReminderBot(token)
    
    # Запускаем бота
    print("🚀 Запускаем бота...")
    asyncio.run(bot.run())